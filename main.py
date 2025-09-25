import asyncio
import pandas as pd
from datetime import datetime
import logging
from typing import List, Dict, Any

from rich.prompt import Prompt, IntPrompt
from rich.table import Table

from debug_utils import (
    check_dependencies,
    setup_logging,
    handle_critical_error,
    print_header,
    console,
    Progress,
    SpinnerColumn,
    TextColumn,
    Panel
)

try:
    check_dependencies()
    from amazon_scraper import AmazonScraper
    from mercadolibre_scraper import MercadoLibreScraper
except ImportError as e:
    console.print(
        Panel(
            f"[bold red]Initialization Error![/bold red]\n\n"
            f"An essential library might be missing or there's an import issue.\n"
            f"Please check the error below and your environment.\n\n"
            f"[italic white]Error: {e}[/italic white]",
            title="[bold yellow]Setup Failure[/bold yellow]",
            border_style="red",
        )
    )
    exit(1)

setup_logging()
logger = logging.getLogger(__name__)


def get_user_input() -> Dict[str, Any]:
    """Gets all necessary input from the user."""
    platforms = {"1": "Amazon", "2": "MercadoLibre", "3": "Both"}
    console.print("[bold]Select a platform to scrape:[/bold]")
    for key, value in platforms.items():
        console.print(f"  [cyan]{key}[/cyan]. {value}")

    choice = Prompt.ask(
        "[bold]Enter your choice[/bold]", choices=["1", "2", "3"], default="3"
    )
    query = Prompt.ask("[bold yellow]What product are you looking for?[/bold yellow]")
    pages = IntPrompt.ask(
        "[bold yellow]How many pages per platform?[/bold yellow]", default=1
    )

    return {"choice": choice, "query": query, "pages": min(pages, 10)}


def display_results_table(products: List[Dict[str, Any]]) -> None:
    """Displays scraped results in a rich Table."""
    if not products:
        console.print("\n[bold red]No products were found.[/bold red]")
        console.print(
            "[yellow]Check 'scraper.log' for a detailed step-by-step report and the 'debug_pages' folder for any saved HTML files.[/yellow]"
        )
        return

    table = Table(
        title=f"Found {len(products)} Unique Products",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Source", style="dim", width=12)
    table.add_column("Product Title", style="cyan", no_wrap=False, max_width=50)
    table.add_column("Price", justify="right", style="green")
    table.add_column("Rating", justify="center")
    table.add_column("Reviews", justify="right")

    for product in sorted(products, key=lambda p: p.get("price") or float("inf"))[:30]:
        price_str = (
            f"{product.get('currency', '$')}{product.get('price'):,.2f}"
            if product.get("price") is not None
            else "[dim]N/A[/dim]"
        )
        rating_str = (
            str(product.get("rating"))
            if product.get("rating")
            else "[dim]N/A[/dim]"
        )
        reviews_str = (
            f"{product.get('review_count'):,}"
            if product.get("review_count") is not None
            else "[dim]N/A[/dim]"
        )

        table.add_row(
            product.get("source", "N/A"),
            product.get("title", "N/A"),
            price_str,
            rating_str,
            reviews_str,
        )
    console.print(table)


def export_to_excel(products: List[Dict[str, Any]], query: str) -> None:
    """Exports data to a formatted Excel file."""
    if not products:
        return

    df = pd.DataFrame(products)
    filename = f"scraped_data_{query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    try:
        with pd.ExcelWriter(filename, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Products")
            worksheet = writer.sheets["Products"]
            for column in worksheet.columns:
                max_length = max(len(str(cell.value)) for cell in column if cell.value)
                worksheet.column_dimensions[
                    column[0].column_letter
                ].width = max(20, max_length + 2)
        console.print(
            f"\n[bold green]Data successfully exported to [underline]{filename}[/underline][/bold green]"
        )
    except Exception as e:
        console.print(f"[bold red]Error exporting to Excel: {e}[/bold red]")


def smart_deduplicate(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicates a list of products using a unique ID."""
    unique_products = {}
    for product in products:
        key = product.get("id")
        if key and key not in unique_products:
            unique_products[key] = product
    return list(unique_products.values())


async def main_logic() -> None:
    """Main async function to orchestrate the scraping process."""
    print_header()
    user_input = get_user_input()

    scrapers = []
    if user_input["choice"] in ["1", "3"]:
        scrapers.append(("Amazon", AmazonScraper()))
    if user_input["choice"] in ["2", "3"]:
        scrapers.append(("MercadoLibre", MercadoLibreScraper(country_code="co")))

    all_products = []
    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True
    ) as progress:
        main_task = progress.add_task(
            "[bold]Scraping Platforms...[/bold]", total=len(scrapers)
        )

        for name, scraper_instance in scrapers:
            progress.update(main_task, description=f"Scraping {name}...")
            try:
                results = await scraper_instance.search_products(
                    user_input["query"], user_input["pages"]
                )
                if results:
                    all_products.extend(results)
                logger.info(
                    f"Scraper '{name}' finished and found {len(results) if results else 0} products."
                )
            except Exception as e:
                logger.error(f"Scraper '{name}' failed entirely: {e}", exc_info=True)
            progress.advance(main_task)

    final_products = smart_deduplicate(all_products)
    display_results_table(final_products)

    if (
        final_products
        and Prompt.ask(
            "\n[bold]Export results to Excel?[/bold]", choices=["y", "n"], default="y"
        )
        == "y"
    ):
        export_to_excel(final_products, user_input["query"])


if __name__ == "__main__":
    try:
        asyncio.run(main_logic())
    except KeyboardInterrupt:
        console.print("\n[bold red]Scraping cancelled by user.[/bold red]")
    except Exception as e:
        handle_critical_error(e)