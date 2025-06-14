import requests
from bs4 import BeautifulSoup
import time
import random
import pandas as pd
from datetime import datetime
import sqlite3
import urllib3
from urllib.parse import quote_plus, urljoin
import logging
import json
import pandas as pd
import cloudscraper
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedAmazonScraper:
    def __init__(self):
        """Initialize scraper with enhanced anti-detection"""
        self.base_url = "https://www.amazon.com"
        self.mobile_base_url = "https://www.amazon.com/gp/aw"
        
        # Setup sessions
        self._setup_enhanced_sessions()
        
        # Enhanced delays
        self.min_delay = 5
        self.max_delay = 10
        
        # Setup database
        self.setup_database()
        
        # Cookie jar for session persistence
        self.cookies = {}
        
        # Test methods
        self._test_methods()
    
    def _setup_enhanced_sessions(self):
        """Setup multiple session types with enhanced configurations"""
        
        # 1. Cloudscraper with enhanced settings
        self.cloudscraper_session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True,
                'mobile': False,
                'custom': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            delay=10,
            interpreter='nodejs',  # Use nodejs interpreter if available
            captcha={
                'provider': 'return_response'  # Return page even with captcha
            }
        )
        
        # 2. Mobile session (often less protected)
        self.mobile_session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'android',
                'mobile': True,
                'custom': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
            }
        )
        
        # 3. Standard session with enhanced configuration
        self.session = requests.Session()
        self.session.verify = False
        
        # Retry strategy
        retry = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 4. API-like session (mimic Amazon app)
        self.api_session = requests.Session()
        self.api_session.verify = False
        
    def _get_enhanced_headers(self, mobile=False):
        """Get enhanced headers with more realistic browser fingerprint"""
        if mobile:
            return {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            }
        else:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
                'Connection': 'keep-alive',
            }
            
            # Add cookies if we have them
            if self.cookies:
                headers['Cookie'] = '; '.join([f'{k}={v}' for k, v in self.cookies.items()])
            
            return headers
    
    def _test_methods(self):
        """Test which methods work"""
        logger.info("[TEST] Testing scraping methods...")
        
        # Test with a simple, common query
        test_queries = ["books", "electronics", "toys"]
        self.working_methods = []
        
        for query in test_queries:
            test_url = f"{self.base_url}/s?k={query}"
            
            methods = [
                ("cloudscraper", lambda: self._test_method(self.cloudscraper_session, test_url)),
                ("mobile", lambda: self._test_method(self.mobile_session, f"{self.mobile_base_url}/s?k={query}")),
                ("api_search", lambda: self._test_api_search(query))
            ]
            
            for method_name, method_func in methods:
                try:
                    if method_func():
                        if method_name not in self.working_methods:
                            self.working_methods.append(method_name)
                            logger.info(f"[TEST] ✓ {method_name} works with query '{query}'!")
                except Exception as e:
                    logger.debug(f"[TEST] {method_name} failed: {e}")
            
            if self.working_methods:
                break
        
        if not self.working_methods:
            logger.warning("[TEST] No methods work - will try all approaches")
            self.working_methods = ["cloudscraper", "mobile", "api_search"]
    
    def _test_method(self, session, url):
        """Test a specific method"""
        response = session.get(url, headers=self._get_enhanced_headers(), timeout=15)
        
        # Save cookies
        if hasattr(response, 'cookies'):
            self.cookies.update(response.cookies)
        
        return self._check_response_valid(response.text)
    
    def _test_api_search(self, query):
        """Test API-style search"""
        # Amazon's autocomplete API (public, no auth needed)
        api_url = f"https://completion.amazon.com/api/2017/suggestions"
        params = {
            'prefix': query,
            'marketplace': 'USA',
            'limit': '11'
        }
        
        response = self.api_session.get(api_url, params=params, timeout=10)
        return response.status_code == 200
    
    def _check_response_valid(self, html):
        """Check if response is valid"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check for bot detection
        if self._is_bot_detected(soup):
            return False
        
        # Check for products
        products = soup.select('div[data-component-type="s-search-result"]')
        if not products:
            products = soup.select('[data-asin]')
        
        return len(products) > 0
    
    def _is_bot_detected(self, soup):
        """Enhanced bot detection check"""
        bot_indicators = [
            lambda s: s.find('form', {'action': '/errors/validateCaptcha'}),
            lambda s: s.find('title') and 'robot' in s.find('title').text.lower(),
            lambda s: 'CBIMarketplaceRedirectOverlay' in str(s),
            lambda s: s.find(string=lambda text: text and 'enter the characters' in text.lower()),
            lambda s: len(s.get_text()) < 1000  # Too little content
        ]
        
        for check in bot_indicators:
            if check(soup):
                return True
        return False
    
    def search_products(self, query, max_pages=2):
        """Enhanced search with multiple strategies"""
        all_products = []
        
        logger.info(f"[SEARCH] Starting enhanced search for: '{query}'")
        
        # Strategy 1: Query variations
        query_strategies = self._generate_smart_queries(query)
        
        for strategy_query in query_strategies:
            logger.info(f"[STRATEGY] Trying: '{strategy_query}'")
            
            # Try each working method
            for method in self.working_methods:
                products = []
                
                try:
                    if method == "cloudscraper":
                        products = self._search_cloudscraper(strategy_query, max_pages)
                    elif method == "mobile":
                        products = self._search_mobile(strategy_query, max_pages)
                    elif method == "api_search":
                        products = self._search_via_api(strategy_query, query)
                    
                    if products:
                        logger.info(f"[SUCCESS] {method} found {len(products)} products")
                        all_products.extend(products)
                        break
                        
                except Exception as e:
                    logger.warning(f"[ERROR] {method} failed: {e}")
            
            # If we found products, stop trying strategies
            if all_products:
                break
            
            # Delay between strategies
            time.sleep(random.uniform(3, 5))
        
        # Remove duplicates
        unique_products = self._deduplicate_products(all_products)
        
        # If still no products, try alternative approach
        if not unique_products:
            logger.info("[FALLBACK] Trying alternative search approach...")
            unique_products = self._fallback_search(query)
        
        logger.info(f"[COMPLETE] Found {len(unique_products)} unique products")
        return unique_products
    
    def _generate_smart_queries(self, query):
        """Generate smarter query variations"""
        queries = []
        words = query.lower().split()
        
        # Original query
        queries.append(query)
        
        # For model numbers like "90d", "z5", etc.
        if any(word for word in words if any(c.isdigit() for c in word)):
            # Try without model number
            base_query = ' '.join([w for w in words if not any(c.isdigit() for c in w)])
            if base_query:
                queries.append(base_query)
            
            # Try brand only (first word)
            if words[0].isalpha():
                queries.append(words[0])
        
        # Try with "camera" or common category
        if len(words) <= 2:
            # Detect category
            camera_brands = ['canon', 'nikon', 'sony', 'fujifilm', 'olympus', 'panasonic']
            if any(brand in query.lower() for brand in camera_brands):
                queries.append(f"{words[0]} camera")
        
        # Remove duplicates
        return list(dict.fromkeys(queries))
    
    def _search_cloudscraper(self, query, max_pages):
        """Search using cloudscraper"""
        products = []
        
        for page in range(1, max_pages + 1):
            url = f"{self.base_url}/s?k={quote_plus(query)}&page={page}"
            
            try:
                # Random delay
                time.sleep(random.uniform(2, 4))
                
                response = self.cloudscraper_session.get(
                    url,
                    headers=self._get_enhanced_headers(),
                    timeout=20
                )
                
                if response.status_code == 200:
                    page_products = self._parse_products(response.text)
                    products.extend(page_products)
                    logger.info(f"[CLOUDSCRAPER] Page {page}: {len(page_products)} products")
                else:
                    logger.warning(f"[CLOUDSCRAPER] Page {page}: Status {response.status_code}")
                
            except Exception as e:
                logger.error(f"[CLOUDSCRAPER] Error on page {page}: {e}")
            
            if page < max_pages:
                time.sleep(random.uniform(self.min_delay, self.max_delay))
        
        return products
    
    def _search_mobile(self, query, max_pages):
        """Search using mobile site (often less protected)"""
        products = []
        
        for page in range(1, max_pages + 1):
            # Mobile URL format
            url = f"{self.mobile_base_url}/s?k={quote_plus(query)}&page={page}"
            
            try:
                response = self.mobile_session.get(
                    url,
                    headers=self._get_enhanced_headers(mobile=True),
                    timeout=20
                )
                
                if response.status_code == 200:
                    # Mobile site has different structure
                    page_products = self._parse_mobile_products(response.text)
                    products.extend(page_products)
                    logger.info(f"[MOBILE] Page {page}: {len(page_products)} products")
                
            except Exception as e:
                logger.error(f"[MOBILE] Error: {e}")
            
            if page < max_pages:
                time.sleep(random.uniform(self.min_delay, self.max_delay))
        
        return products
    
    def _search_via_api(self, search_query, original_query):
        """Use Amazon's public APIs to find products"""
        products = []
        
        try:
            # Step 1: Get suggestions from autocomplete API
            api_url = "https://completion.amazon.com/api/2017/suggestions"
            params = {
                'prefix': search_query,
                'marketplace': 'USA',
                'limit': '50'
            }
            
            response = self.api_session.get(api_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                suggestions = data.get('suggestions', [])
                
                # Extract product ASINs from suggestions
                for suggestion in suggestions:
                    if suggestion.get('type') == 'PRODUCT':
                        product = {
                            'asin': suggestion.get('value'),
                            'title': suggestion.get('refTag', ''),
                            'price': None,
                            'rating': None,
                            'review_count': None,
                            'url': f"{self.base_url}/dp/{suggestion.get('value')}"
                        }
                        
                        # Filter by original query
                        if original_query.lower() in product['title'].lower():
                            products.append(product)
                
                logger.info(f"[API] Found {len(products)} products via autocomplete")
        
        except Exception as e:
            logger.error(f"[API] Error: {e}")
        
        return products
    
    def _parse_products(self, html):
        """Parse products from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        if self._is_bot_detected(soup):
            logger.warning("[PARSE] Bot detection triggered")
            self._save_debug_html(html, "bot_detected")
            return []
        
        products = []
        
        # Try multiple selectors
        selectors = [
            'div[data-component-type="s-search-result"]',
            'div[data-asin]:has(h2)',
            '[data-index][data-asin]',
            '.s-result-item[data-asin]',
            'div.sg-col-inner'
        ]
        
        containers = []
        for selector in selectors:
            containers = soup.select(selector)
            if containers:
                logger.debug(f"[PARSE] Using selector: {selector} ({len(containers)} items)")
                break
        
        for container in containers:
            try:
                product = self._extract_product_info(container)
                if product:
                    products.append(product)
            except Exception as e:
                logger.debug(f"[PARSE] Failed to parse item: {e}")
        
        return products
    
    def _parse_mobile_products(self, html):
        """Parse products from mobile site"""
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        
        # Mobile selectors are different
        mobile_selectors = [
            'div[data-asin]',
            '.aw-search-results div[data-asin]',
            'span[data-component-type="s-product-image"]'
        ]
        
        for selector in mobile_selectors:
            containers = soup.select(selector)
            if containers:
                break
        
        for container in containers:
            try:
                # Mobile extraction logic
                product = self._extract_mobile_product(container)
                if product:
                    products.append(product)
            except Exception as e:
                logger.debug(f"[MOBILE PARSE] Error: {e}")
        
        return products
    
    def _extract_product_info(self, container):
        """Extract product information"""
        product = {}
        
        # ASIN
        asin = container.get('data-asin')
        if not asin:
            asin_elem = container.find(attrs={'data-asin': True})
            if asin_elem:
                asin = asin_elem.get('data-asin')
        
        if not asin or asin == "":
            return None
        
        product['asin'] = asin
        
        # Title
        title_selectors = [
            'h2 a span',
            'h2 span',
            '.a-size-base-plus',
            '.a-size-medium.a-text-normal',
            '[data-cy="title-recipe"] span'
        ]
        
        for selector in title_selectors:
            title_elem = container.select_one(selector)
            if title_elem and title_elem.text.strip():
                product['title'] = title_elem.text.strip()
                break
        
        if not product.get('title'):
            return None
        
        # URL
        link = container.select_one('h2 a')
        if link:
            product['url'] = urljoin(self.base_url, link.get('href', ''))
        else:
            product['url'] = f"{self.base_url}/dp/{asin}"
        
        # Price
        price_selectors = [
            '.a-price .a-offscreen',
            '.a-price-whole',
            '.a-price span:first-child',
            '.a-price-range .a-price .a-offscreen'
        ]
        
        for selector in price_selectors:
            price_elem = container.select_one(selector)
            if price_elem:
                try:
                    price_text = price_elem.text.strip()
                    price = float(price_text.replace('$', '').replace(',', '').split('-')[0])
                    product['price'] = price
                    break
                except:
                    continue
        
        # Rating
        rating_elem = container.select_one('.a-icon-alt')
        if rating_elem:
            try:
                rating = float(rating_elem.text.split()[0])
                product['rating'] = rating
            except:
                pass
        
        # Review count
        review_elem = container.select_one('[aria-label*="ratings"]')
        if review_elem:
            try:
                aria_label = review_elem.get('aria-label', '')
                review_count = int(''.join(filter(str.isdigit, aria_label.split(',')[0])))
                product['review_count'] = review_count
            except:
                pass
        
        return product
    
    def _extract_mobile_product(self, container):
        """Extract product from mobile layout"""
        # Similar to regular extraction but with mobile-specific selectors
        return self._extract_product_info(container)
    
    def _fallback_search(self, query):
        """Fallback search using category browsing"""
        products = []
        
        # Try to browse by category
        category_urls = {
            'camera': '/s?i=electronics&rh=n%3A502394',
            'laptop': '/s?i=computers&rh=n%3A565108',
            'phone': '/s?i=electronics&rh=n%3A2811119011'
        }
        
        # Detect category
        for category, url in category_urls.items():
            if category in query.lower():
                logger.info(f"[FALLBACK] Browsing {category} category")
                
                try:
                    response = self.cloudscraper_session.get(
                        self.base_url + url,
                        headers=self._get_enhanced_headers(),
                        timeout=20
                    )
                    
                    if response.status_code == 200:
                        products = self._parse_products(response.text)
                        # Filter by query
                        products = [p for p in products if query.lower() in p.get('title', '').lower()]
                        
                except Exception as e:
                    logger.error(f"[FALLBACK] Error: {e}")
                
                break
        
        return products
    
    def _deduplicate_products(self, products):
        """Remove duplicate products"""
        seen = set()
        unique = []
        
        for product in products:
            if product['asin'] not in seen:
                seen.add(product['asin'])
                unique.append(product)
        
        return unique
    
    def _save_debug_html(self, html, prefix):
        """Save HTML for debugging"""
        filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html[:10000])  # First 10k chars
        logger.info(f"[DEBUG] Saved HTML to {filename}")
    
    def setup_database(self):
        """Setup database"""
        self.conn = sqlite3.connect('amazon_products_enhanced.db')
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT,
                title TEXT,
                price REAL,
                rating REAL,
                review_count INTEGER,
                url TEXT,
                search_query TEXT,
                method TEXT,
                scraped_at TIMESTAMP,
                UNIQUE(asin)
            )
        ''')
        self.conn.commit()
    
    def save_products(self, products, search_query):
        """Save products to database"""
        timestamp = datetime.now()
        saved = 0
        
        for product in products:
            try:
                self.cursor.execute('''
                    INSERT OR REPLACE INTO products 
                    (asin, title, price, rating, review_count, url, search_query, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    product.get('asin'),
                    product.get('title'),
                    product.get('price'),
                    product.get('rating'),
                    product.get('review_count'),
                    product.get('url'),
                    search_query,
                    timestamp
                ))
                saved += 1
            except Exception as e:
                logger.error(f"[DB] Save error: {e}")
        
        self.conn.commit()
        logger.info(f"[DB] Saved {saved} products")
    
    def display_results(self, products):
        """Display results"""
        if not products:
            print("\n❌ No se encontraron productos")
            return
        
        print(f"\n{'='*80}")
        print(f"✅ ENCONTRADOS {len(products)} PRODUCTOS")
        print(f"{'='*80}")
        
        for i, product in enumerate(products[:20], 1):
            print(f"\n{i}. {product['title'][:70]}...")
            
            if product.get('price'):
                print(f"   💰 Precio: ${product['price']:.2f}")
            else:
                print(f"   💰 Precio: No disponible")
            
            if product.get('rating'):
                stars = '⭐' * int(product['rating'])
                print(f"   {stars} {product['rating']}/5.0", end="")
                if product.get('review_count'):
                    print(f" ({product['review_count']} reviews)")
                else:
                    print()
            
            print(f"   🔗 ASIN: {product['asin']}")
            print(f"   📎 URL: {product['url'][:50]}...")
            print("-" * 60)
    
    def close(self):
        """Cleanup"""
        self.conn.close()

def main():
    print("\n🚀 AMAZON SCRAPER MEJORADO")
    print("=" * 50)
    print("Características:")
    print("✓ Múltiples métodos de búsqueda")
    print("✓ Detección inteligente de categorías")
    print("✓ Búsqueda móvil como respaldo")
    print("✓ API de autocompletado")
    print("=" * 50)
    
    scraper = EnhancedAmazonScraper()
    
    try:
        # Get query
        query = input("\n¿Qué producto buscas? ").strip()
        if not query:
            print("❌ No ingresaste ningún producto")
            return
        
        # Get pages
        try:
            pages = int(input("¿Cuántas páginas? (1-3, default=1): ") or "1")
            pages = max(1, min(pages, 3))
        except:
            pages = 1
        
        print(f"\n🔍 Buscando '{query}'...")
        print("⏳ Esto puede tomar unos momentos...\n")
        
        # Search
        products = scraper.search_products(query, pages)
        
        if products:
            # Save
            scraper.save_products(products, query)
            
            # Display
            scraper.display_results(products)
            
            # Export
            if input("\n¿Exportar a CSV? (s/n): ").lower() == 's':
                df = pd.DataFrame(products)
                filename = f"amazon_{query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df.to_csv(filename, index=False)
                print(f"✅ Exportado a {filename}")
        else:
            print("\n❌ No se encontraron productos")
            print("\n💡 Sugerencias:")
            print("1. Intenta con términos más simples (ej: 'canon' en vez de 'canon 90d')")
            print("2. Espera unos minutos antes de intentar de nuevo")
            print("3. Considera usar una VPN")
            print("4. Revisa los archivos HTML de debug generados")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Búsqueda cancelada")
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()

if __name__ == "__main__":
    main()