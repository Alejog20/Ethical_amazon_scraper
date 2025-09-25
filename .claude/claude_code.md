# Claude Code Configuration for Ethical E-Commerce Scraper

## Project Context
This is an enterprise-grade, ethical multi-platform e-commerce scraper designed for educational purposes. The scraper implements a 5-layer resilience funnel with advanced anti-detection techniques for Amazon and MercadoLibre.

## Key Technologies
- **Language**: Python 3.8+ with asyncio
- **Web Scraping**: httpx, selectolax, playwright, playwright-stealth
- **UI/UX**: rich (console interface)
- **Data Processing**: pandas, openpyxl
- **Testing**: unittest (custom framework)

## Project Structure
- `main.py` - Entry point and orchestrator
- `amazon_scraper.py` - Amazon-specific scraper with stealth browser automation
- `mercadolibre_scraper.py` - MercadoLibre scraper with API + HTML fallback
- `debug_utils.py` - Shared utilities (caching, logging, UI components)
- `test_scrapers.py` - Unit testing framework for offline validation
- `test_data/` - Static HTML files for testing

## Code Style Guidelines
- Follow PEP 8 standards
- Use type hints for all function parameters and returns
- Maintain async/await patterns consistently
- Prioritize readability and maintainability
- Add comprehensive error handling and logging
- Use descriptive variable and function names

## Security & Ethics
- This project is for educational purposes only
- Implements respectful scraping with delays and caching
- Follows robots.txt guidelines
- Users must comply with website Terms of Service
- No credential harvesting or malicious activities

## Testing Strategy
- Unit tests use static HTML files (no live requests)
- Tests validate parser correctness against website changes
- Comprehensive data validation and type checking
- Offline-first testing approach for reliable CI/CD

## Performance Considerations
- Implements caching to reduce server load
- Uses connection pooling with httpx
- Employs exponential backoff for failed requests
- Optimizes for minimal resource usage

## Claude Code Specific Instructions
When working on this project:
1. Always test scrapers with the unit test framework first
2. Respect the 5-layer strategy funnel architecture
3. Maintain detailed logging for debugging
4. Validate all extracted data before processing
5. Follow ethical scraping practices consistently