import requests
from bs4 import BeautifulSoup
import urllib3
from fake_useragent import UserAgent
import json

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def debug_amazon_response():
    """Debug what Amazon is actually returning"""
    
    # Setup session with SSL bypass
    session = requests.Session()
    session.verify = False
    ua = UserAgent()
    
    headers = {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    search_query = "nikon z5"
    search_url = "https://www.amazon.com/s"
    params = {'k': search_query, 'page': 1}
    
    print("=" * 60)
    print("AMAZON RESPONSE DEBUGGER")
    print("=" * 60)
    
    try:
        print(f"1. Sending request to Amazon for: {search_query}")
        print(f"   URL: {search_url}?k={search_query}")
        print(f"   User-Agent: {headers['User-Agent'][:50]}...")
        
        response = session.get(search_url, params=params, headers=headers, timeout=15)
        
        print(f"\n2. Response received:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Content Length: {len(response.text)} characters")
        print(f"   Final URL: {response.url}")
        
        if response.status_code != 200:
            print(f"   ERROR: Non-200 status code")
            return
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        print(f"\n3. Page Analysis:")
        
        # Check for CAPTCHA
        captcha_check = soup.find('form', {'action': '/errors/validateCaptcha'})
        if captcha_check:
            print("   ❌ CAPTCHA detected! Amazon is blocking automated requests.")
            return
        
        # Check for robot check
        robot_check = soup.find(string=lambda text: text and 'robot' in text.lower())
        if robot_check:
            print("   ❌ Robot detection page detected!")
            print(f"   Message: {robot_check[:100]}...")
            return
        
        # Check page title
        title = soup.find('title')
        if title:
            print(f"   Page Title: {title.get_text()[:100]}...")
        
        # Look for search results containers
        print(f"\n4. Searching for product containers:")
        
        # Try different selectors Amazon uses
        selectors_to_try = [
            ('div[data-component-type="s-search-result"]', 'Standard search results'),
            ('div[data-asin]', 'ASIN containers'),
            ('[data-cy="title-recipe-title"]', 'Title recipe'),
            ('.s-result-item', 'Result items'),
            ('.s-widget-container', 'Widget containers'),
            ('[cel_widget_id*="MAIN-SEARCH_RESULTS"]', 'Main search results'),
        ]
        
        found_any = False
        for selector, description in selectors_to_try:
            elements = soup.select(selector)
            print(f"   {description}: {len(elements)} found")
            if elements:
                found_any = True
                # Show first element's structure
                print(f"      First element classes: {elements[0].get('class', [])}")
                if elements[0].get('data-asin'):
                    print(f"      ASIN: {elements[0].get('data-asin')}")
        
        if not found_any:
            print("   ❌ No product containers found with any selector!")
        
        # Check for specific Amazon elements
        print(f"\n5. Amazon-specific checks:")
        
        # Search for any text mentioning results
        results_text = soup.find(string=lambda text: text and 'results' in text.lower())
        if results_text:
            print(f"   Found results text: {results_text.strip()[:100]}...")
        
        # Look for pagination
        pagination = soup.find('span', class_='s-pagination-strip')
        if pagination:
            print(f"   Pagination found: Yes")
        else:
            print(f"   Pagination found: No")
        
        # Check for no results message
        no_results = soup.find(string=lambda text: text and 'no results' in text.lower())
        if no_results:
            print(f"   No results message: {no_results.strip()}")
        
        # Save raw HTML for inspection (first 5000 chars)
        print(f"\n6. Raw HTML sample (first 2000 characters):")
        print("-" * 40)
        print(response.text[:2000])
        print("-" * 40)
        
        # Save full HTML to file for inspection
        with open('amazon_debug_response.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"\n✅ Full HTML saved to 'amazon_debug_response.html'")
        print("   Open this file in a browser to see what Amazon returned")
        
    except Exception as e:
        print(f"❌ Error during debug: {e}")

def test_different_search_terms():
    """Test with different search terms to see if it's query-specific"""
    
    session = requests.Session()
    session.verify = False
    ua = UserAgent()
    
    headers = {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    test_queries = ["laptop", "mouse", "book", "headphones", "nikon z5"]
    
    print("\n" + "=" * 60)
    print("TESTING DIFFERENT SEARCH TERMS")
    print("=" * 60)
    
    for query in test_queries:
        try:
            response = session.get(
                "https://www.amazon.com/s",
                params={'k': query},
                headers=headers,
                timeout=10
            )
            
            soup = BeautifulSoup(response.text, 'html.parser')
            products = soup.select('div[data-component-type="s-search-result"]')
            
            print(f"Query '{query}': {response.status_code} status, {len(products)} products found")
            
        except Exception as e:
            print(f"Query '{query}': Failed - {e}")

if __name__ == "__main__":
    debug_amazon_response()
    test_different_search_terms()