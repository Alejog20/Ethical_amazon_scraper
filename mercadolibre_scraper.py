import asyncio
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

import httpx
from selectolax.parser import HTMLParser, Node

from debug_utils import (
    FileCache,
    get_random_user_agent,
    get_realistic_headers,
    retry_with_backoff,
    validate_product_data,
    is_retryable_error,
    log_html_snippet,
    save_debug_html,
    console,
)

logger = logging.getLogger(__name__)


class MercadoLibreScraper:
    def __init__(self, country_code: str = "co") -> None:
        self.base_url = f"https://www.mercadolibre.com.{country_code}"
        self.api_url = f"https://api.mercadolibre.com/sites/MCO/search"
        self.cache = FileCache()

    async def search_products(self, query: str, max_pages: int) -> List[Dict[str, Any]]:
        logger.info(f"--- Starting MercadoLibre Search for '{query}' ---")
        async with httpx.AsyncClient(
            http2=True, timeout=30.0, follow_redirects=True, verify=False
        ) as client:
            all_products = []
            for page_num in range(1, max_pages + 1):
                console.log(f"[MercadoLibre] Scraping page {page_num}/{max_pages} for '{query}'...")
                products = await self._execute_strategy_funnel(client, query, page_num)
                if products is None:
                    logger.warning(f"[MercadoLibre] Page {page_num}: Critical failure. Stopping search.")
                    break
                all_products.extend(products)
                if not products and page_num == 1:
                    logger.warning("[MercadoLibre] Page 1: No products found. Stopping search.")
                    break

        final_products = self._deduplicate(all_products)
        logger.info(f"--- MercadoLibre Search Finished. Found {len(final_products)} total products. ---")
        return final_products

    async def _execute_strategy_funnel(
        self, client: httpx.AsyncClient, query: str, page_num: int
    ) -> Optional[List[Dict[str, Any]]]:
        logger.info(f"[MercadoLibre] Page {page_num}: Executing Strategy Funnel...")

        logger.info(f"[MercadoLibre] Page {page_num}: -> [ATTEMPT] Strategy 2: API Request...")
        api_data = await self._fetch_with_api(client, query, page_num)
        if api_data:
            products = self._parse_api_data(api_data)
            if products:
                logger.info(f"[MercadoLibre] Page {page_num}:    -> [SUCCESS] Strategy 2 SUCCEEDED. Found {len(products)} products.")
                return products
            logger.warning(f"[MercadoLibre] Page {page_num}:    -> [RESULT] API returned no products.")

        logger.warning(f"[MercadoLibre] Page {page_num}: -> [ATTEMPT] Strategy 3: Desktop HTTPX...")
        desktop_html = await self._fetch_with_html(client, query, page_num)
        if desktop_html:
            products, is_valid = self._parse_html(desktop_html)
            if is_valid and products:
                logger.info(f"[MercadoLibre] Page {page_num}:    -> [SUCCESS] Strategy 3 SUCCEEDED. Found {len(products)} products.")
                return products
            logger.warning(f"[MercadoLibre] Page {page_num}:    -> [RESULT] Strategy 3 FAILED. Page invalid or no products.")

        logger.error(f"[MercadoLibre] Page {page_num}: All strategies FAILED.")
        return []

    async def _fetch_with_api(
        self, client: httpx.AsyncClient, query: str, page_num: int
    ) -> Optional[Dict[str, Any]]:
        offset = (page_num - 1) * 50
        params = {"q": query, "offset": offset, "limit": 50}
        try:
            response = await client.get(self.api_url, params=params)
            logger.info(f"HTTP Request: GET {response.url} \"{response.status_code} {response.reason_phrase}\"")
            if response.status_code == 200:
                return response.json()
            logger.warning(f"[MercadoLibre] API fetch returned status {response.status_code}")
            return None
        except httpx.RequestError as e:
            logger.error(f"[MercadoLibre] API fetch failed. Error: {e}")
            return None

    async def _fetch_with_html(
        self, client: httpx.AsyncClient, query: str, page_num: int
    ) -> Optional[str]:
        url = self._get_url(query, page_num)
        if (html := self.cache.get(url)) is not None:
            return html

        headers = get_realistic_headers(is_mobile=False)

        async def make_request() -> str:
            response = await client.get(url, headers=headers)
            logger.info(f"HTTP Request: GET {url} \"{response.status_code} {response.reason_phrase}\"")

            if response.status_code == 200:
                self.cache.set(url, response.text)
                return response.text
            elif is_retryable_error(response.status_code):
                raise httpx.HTTPStatusError(f"Retryable HTTP error: {response.status_code}", request=response.request, response=response)
            else:
                logger.warning(f"[MercadoLibre] HTML fetch for {url} returned non-retryable status {response.status_code}")
                return None

        try:
            result = await retry_with_backoff(make_request, max_retries=3)
            return result
        except Exception as e:
            logger.error(f"[MercadoLibre] HTML fetch failed for {url} after retries. Error: {e}")
            return None

    def _parse_api_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = data.get("results", [])
        if not results:
            return []

        products = []
        for item in results:
            products.append({
                "id": item.get("id"),
                "source": "MercadoLibre",
                "title": item.get("title"),
                "url": item.get("permalink"),
                "price": item.get("price"),
                "currency": item.get("currency_id"),
                "rating": None,
                "review_count": None,
            })
        return products

    def _parse_html(self, html: str) -> Tuple[List[Dict[str, Any]], bool]:
        tree = HTMLParser(html)
        if not self._is_valid_page(tree):
            save_debug_html(html, "mercadolibre_invalid_page")
            return [], False

        selectors = [
            "li.ui-search-layout__item",
            "div.ui-search-result__wrapper",
            ".poly-card",
            ".ui-search-results__item"
        ]
        container = next((tree.css(s) for s in selectors if tree.css(s)), [])

        if not container:
            logger.warning("[MercadoLibre] PARSE: Could not find product containers with any selector.")
            save_debug_html(html, "mercadolibre_no_containers")
            return [], False

        logger.info(f"[MercadoLibre] PARSE: Found {len(container)} product containers.")
        products = []
        for item in container:
            product = self._extract_product_info(item)
            if product:
                products.append(product)

        logger.info(f"[MercadoLibre] PARSE: Successfully extracted {len(products)} products.")
        return products, True

    def _is_valid_page(self, tree: HTMLParser) -> bool:
        logger.info("[MercadoLibre] Page Analysis: Validating page content...")
        if "No hay publicaciones que coincidan con tu búsqueda" in tree.body.text():
            logger.warning("[MercadoLibre] Page Analysis: 'No results' page detected.")
            return False
        logger.info("[MercadoLibre] Page Analysis: Page appears valid.")
        return True

    def _extract_product_info(self, item: Node) -> Optional[Dict[str, Any]]:
        title = None
        title_selectors = [
            "img[title]",
            "h2.ui-search-item__title",
            ".ui-search-item__title",
            "h2 a",
            "[data-testid*='title']"
        ]

        for selector in title_selectors:
            if selector == "img[title]":
                img_node = item.css_first(selector)
                if img_node and img_node.attributes.get("title"):
                    title = img_node.attributes["title"].strip()
                    break
            else:
                title_node = item.css_first(selector)
                if title_node and title_node.text(strip=True):
                    title = title_node.text(strip=True)
                    break

        if not title:
            log_html_snippet(logger, "MercadoLibre", "title", item.html)
            return None

        url = None
        url_selectors = [
            "a.ui-search-link",
            "a[href*='MLA']",
            "a[href*='MCO']",
            "h2 a",
            "a.poly-component__title"
        ]

        for selector in url_selectors:
            url_node = item.css_first(selector)
            if url_node and url_node.attributes.get("href"):
                url = url_node.attributes["href"]
                break

        price = None
        price_selectors = [
            "span.andes-money-amount__fraction",
            ".andes-money-amount__fraction",
            ".price-tag-fraction",
            "[data-testid*='price']",
            ".poly-price__current .poly-price__fraction"
        ]

        for selector in price_selectors:
            price_node = item.css_first(selector)
            if price_node and price_node.text(strip=True):
                try:
                    price_text = price_node.text(strip=True)
                    if price_text.count('.') > 1:
                        price_text = price_text.replace('.', '')
                    elif '.' in price_text and len(price_text.split('.')[-1]) <= 2:
                        price_text = price_text.replace('.', '')
                    price = float(price_text)
                    break
                except (ValueError, TypeError):
                    continue

        if price is None:
            log_html_snippet(logger, "MercadoLibre", "price", item.html)

        product_id = None
        if url:
            try:
                id_match = re.search(r'(MLA|MCO)([0-9]+)', url)
                if id_match:
                    product_id = id_match.group(0)
                else:
                    url_parts = url.split('/')
                    for part in url_parts:
                        if part and not part.startswith('http') and len(part) > 5:
                            product_id = part.split('-')[0] if '-' in part else part
                            break
            except (IndexError, AttributeError):
                log_html_snippet(logger, "MercadoLibre", "product_id", item.html)

        currency = "$"
        currency_selectors = [
            "span.andes-money-amount__currency-symbol",
            ".andes-money-amount__currency-symbol",
            ".price-tag-symbol",
            ".poly-price__symbol"
        ]

        for selector in currency_selectors:
            currency_node = item.css_first(selector)
            if currency_node and currency_node.text(strip=True):
                currency = currency_node.text(strip=True)
                break

        raw_product = {
            "id": product_id,
            "source": "MercadoLibre",
            "title": title,
            "url": url,
            "price": price,
            "currency": currency,
            "rating": None,
            "review_count": None,
        }

        validated_product = validate_product_data(raw_product)
        return validated_product

    def _get_url(self, query: str, page_num: int) -> str:
        q = query.replace(" ", "-")
        if page_num == 1:
            return f"https://listado.mercadolibre.com.co/{q}"
        else:
            offset = (page_num - 1) * 50
            return f"https://listado.mercadolibre.com.co/{q}_Desde_{offset+1}"

    def _get_headers(self, is_mobile: bool = False) -> Dict[str, str]:
        return get_realistic_headers(is_mobile)

    def _deduplicate(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return list({p["id"]: p for p in products}.values())