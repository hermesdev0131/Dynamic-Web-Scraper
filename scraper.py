#!/usr/bin/env python3
"""
Enhanced scraper that:
1. Extracts product names and URLs from collection pages
2. Visits each product URL to extract prices and sizes
3. Handles dynamic pricing based on size selection

Includes a lightweight mode (no Selenium) suitable for low-memory environments
by using requests + BeautifulSoup and parsing Shopify product JSON.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import time
import json
import csv
import re
import requests
from urllib.parse import urljoin


def setup_driver():
    """Setup Chrome driver with options (optimized for low-memory environments)"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    # Additional flags to reduce memory/CPU footprint
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-client-side-phishing-detection")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-hang-monitor")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--metrics-recording-only")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--safebrowsing-disable-auto-update")
    chrome_options.add_argument("--disable-features=Translate,BackForwardCache,site-per-process")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    # Uncomment if absolutely needed in super constrained environments (can be unstable)
    # chrome_options.add_argument("--single-process")
    # chrome_options.add_argument("--no-zygote")
    return webdriver.Chrome(options=chrome_options)


def format_price(price_text):
    """Format price to €X,XX format with comma/period conversion"""
    if not price_text:
        return None
    # Extract numbers and currency symbols from the price text
    cleaned_price = re.sub(r"[^\d.,€$£¥₹]", "", price_text.strip())
    numeric_part = cleaned_price
    # Swap separators for EU-style formatting
    numeric_part = numeric_part.replace('.', '#').replace(',', '.').replace('#', ',')
    return numeric_part


# -----------------------------
# Lightweight (no-Selenium) mode
# -----------------------------

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}


def _get(url, timeout=30):
    """HTTP GET with sane headers and timeout."""
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp


def extract_products_from_collection_light(url, max_pages=3, max_products=None):
    """Extract product names and URLs from Shopify collection pages via HTTP.

    - Uses page-based pagination (?page=N)
    - Stops when no items found, after max_pages, or when max_products collected
    """
    all_products = []
    page = 1
    base = "https://www.rainshadowlabs.com"

    while True:
        if max_pages and page > max_pages:
            break

        page_url = url if page == 1 else (url + ("&" if "?" in url else "?") + f"page={page}")
        try:
            resp = _get(page_url, timeout=40)
        except Exception as e:
            print(f"Warning: failed to GET collection page {page}: {e}")
            break

        soup = BeautifulSoup(resp.text, 'html.parser')
        product_grid = soup.find('ul', id='product-grid')
        if not product_grid:
            # Try common alternative containers
            product_grid = soup.select_one('ul.product-grid, div#product-grid, div.product-grid')
        if not product_grid:
            if page == 1:
                print("Warning: Could not find product grid on first page")
            break

        items = product_grid.find_all('li') or product_grid.find_all('div', recursive=True)
        page_products = []
        for item in items:
            link_elem = item.find('a', href=True)
            if not link_elem:
                continue
            href = link_elem.get('href')
            if not href:
                continue
            product_url = urljoin(base, href)

            product_name = link_elem.get_text(strip=True)
            if not product_name:
                # Try nested elements
                name_selectors = ['.product-title', '.product-name', 'h2', 'h3', 'h4', '.title']
                for selector in name_selectors:
                    name_elem = link_elem.select_one(selector) or item.select_one(selector)
                    if name_elem:
                        product_name = name_elem.get_text(strip=True)
                        break

            if product_name:
                page_products.append({
                    'name': product_name,
                    'url': product_url
                })

            if max_products and (len(all_products) + len(page_products)) >= max_products:
                break

        if page_products:
            all_products.extend(page_products)
        else:
            # No products on this page -> stop
            break

        if max_products and len(all_products) >= max_products:
            break

        page += 1

    return all_products


def _format_cents_to_price_text(cents, currency_symbol="$"):
    """Convert integer cents to currency text like $10.00.
    We'll pass it through format_price to match output style.
    """
    try:
        amount = int(cents) / 100.0
        return f"{currency_symbol}{amount:.2f}"
    except Exception:
        return None


def _parse_shopify_product_json(soup):
    """Try to parse Shopify product JSON from script tags."""
    # Common patterns: script[type="application/json"][data-product],
    # script#ProductJson-... or other theme-specific variations
    for script in soup.find_all('script'):
        t = (script.get('type') or '').lower()
        if 'json' not in t:
            continue
        raw = script.string or script.get_text(strip=True)
        if not raw:
            continue
        if '"variants"' not in raw and 'variants"' not in raw:
            continue
        try:
            data = json.loads(raw)
            # Some themes wrap under 'product'
            if isinstance(data, dict) and 'variants' in data:
                return data
            if isinstance(data, dict) and 'product' in data and isinstance(data['product'], dict) and 'variants' in data['product']:
                return data['product']
        except Exception:
            continue
    return None


def extract_product_details_light(product_url, product_name):
    """Extract sizes and prices by parsing Shopify product JSON via HTTP.

    Strategy:
    1) Try the official Shopify product endpoint <product_url>.json (most reliable)
    2) Fallback to parsing embedded JSON in the HTML
    3) As a last resort, scrape a single price from .price__container
    """
    print(f"  [light] Extracting details for: {product_name}")

    def _product_json_url(url: str) -> str:
        # Build <product_url>.json (strip queries/fragments)
        from urllib.parse import urlparse, urlunparse
        p = urlparse(url)
        path = p.path
        if path.endswith('/'):
            path = path[:-1]
        if not path.endswith('.json'):
            path = f"{path}.json"
        return urlunparse((p.scheme, p.netloc, path, '', '', ''))

    def _parse_price_cents(value):
        # Normalize variant price to integer cents
        try:
            if value is None:
                return None
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                # Heuristic: small numbers like 7.0 => dollars; large like 700 => cents
                return int(round(value * 100)) if value < 1000 else int(value)
            if isinstance(value, str):
                v = value.strip()
                if v.isdigit():
                    return int(v)
                # Try float dollars
                return int(round(float(v) * 100))
        except Exception:
            return None
        return None

    try:
        product_details = {
            'name': product_name,
            'url': product_url,
            'size_price_combinations': []
        }

        data = None
        # 1) Try product JSON endpoint
        try:
            pj_url = _product_json_url(product_url)
            pj_resp = _get(pj_url, timeout=40)
            pj = pj_resp.json()
            if isinstance(pj, dict) and 'product' in pj and isinstance(pj['product'], dict):
                data = pj['product']
            elif isinstance(pj, dict) and 'variants' in pj:
                data = pj
        except Exception:
            data = None

        soup = None
        if not data:
            # 2) Fallback to embedded JSON in HTML
            resp = _get(product_url, timeout=40)
            soup = BeautifulSoup(resp.text, 'html.parser')
            data = _parse_shopify_product_json(soup)

        if not data:
            # 3) Last resort: read a single price from page
            if soup is None:
                resp = _get(product_url, timeout=40)
                soup = BeautifulSoup(resp.text, 'html.parser')
            price_container = soup.select_one('.price__container')
            if price_container:
                raw_price = price_container.get_text(strip=True)
                formatted = format_price(raw_price)
                if formatted:
                    product_details['size_price_combinations'].append({'size': 'Standard', 'price': formatted})
            return product_details

        # Currency symbol (default USD)
        currency_symbol = '$'

        variants = data.get('variants', []) if isinstance(data, dict) else []
        options = data.get('options', []) if isinstance(data, dict) else []

        # Determine which option index represents size (if any)
        size_option_index = None
        if options:
            # Shopify .json typically has list of dicts: [{'name': 'Size', ...}, ...]
            if isinstance(options[0], dict):
                for i, opt in enumerate(options):
                    if str(opt.get('name', '')).strip().lower() == 'size':
                        size_option_index = i  # 0-based
                        break

        for v in variants:
            # Prefer explicit size option if present
            size_text = None
            if size_option_index is not None:
                size_text = v.get(f'option{size_option_index + 1}')

            # Fallbacks
            if not size_text:
                size_text = (
                    v.get('option1') or v.get('option2') or v.get('option3') or v.get('title') or 'Variant'
                )

            # Clean size text
            if isinstance(size_text, str):
                if size_text.lower() == 'default title':
                    size_text = 'Standard'
                if 'sample' in size_text.lower():
                    size_text = size_text.replace('sample', '').replace('Sample', '').strip()

            # Price normalization
            price_cents = _parse_price_cents(v.get('price'))
            if price_cents is None:
                price_cents = _parse_price_cents(v.get('price_cents'))

            if price_cents is not None:
                price_text = _format_cents_to_price_text(price_cents, currency_symbol)
                formatted_price = format_price(price_text)
                product_details['size_price_combinations'].append({
                    'size': size_text,
                    'price': formatted_price
                })

        # Deduplicate
        seen = set()
        unique = []
        for combo in product_details['size_price_combinations']:
            key = (combo['size'], combo['price'])
            if key not in seen:
                seen.add(key)
                unique.append(combo)
        product_details['size_price_combinations'] = unique
        return product_details

    except Exception as e:
        print(f"    [light] Error extracting details from {product_url}: {e}")
        return {
            'name': product_name,
            'url': product_url,
            'size_price_combinations': [],
            'error': str(e)
        }


# -----------------------------
# Original Selenium-based helpers
# -----------------------------

def extract_products_from_collection(driver, url):
    """Extract product names and URLs from collection page with pagination"""
    all_products = []
    
    try:
        driver.get(url)
        time.sleep(5)
        
        # Scroll to load content
        for i in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        
        page_number = 1
        
        while True:
            print(f"Scraping collection page {page_number}...")
            
            # Get current page source and extract products
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Find the ul element with id="product-grid"
            product_grid = soup.find('ul', id='product-grid')
            
            if not product_grid:
                print("Warning: Could not find ul#product-grid element")
                break
            
            # Find all li elements within the product grid
            product_items = product_grid.find_all('li')
            page_products = []
            
            for item in product_items:
                product_info = {}
                
                # Find the first link in the item
                link_elem = item.find('a', href=True)
                if link_elem:
                    href = link_elem.get('href')
                    if href:
                        # Handle relative URLs
                        if href.startswith('/'):
                            product_info['url'] = f"https://www.rainshadowlabs.com{href}"
                        else:
                            product_info['url'] = href
                        
                        # Extract product name from the link text or nested elements
                        product_name = link_elem.get_text(strip=True)
                        
                        # If link text is empty, try to find name in nested elements
                        if not product_name:
                            name_selectors = ['.product-title', '.product-name', 'h2', 'h3', 'h4', '.title']
                            for selector in name_selectors:
                                name_elem = link_elem.select_one(selector)
                                if name_elem:
                                    product_name = name_elem.get_text(strip=True)
                                    break
                        
                        if product_name:
                            product_info['name'] = product_name
                
                # Also try to find product name outside of links
                if not product_info.get('name'):
                    name_selectors = ['.product-title', '.product-name', 'h2', 'h3', 'h4', '.title']
                    for selector in name_selectors:
                        name_elem = item.select_one(selector)
                        if name_elem:
                            product_info['name'] = name_elem.get_text(strip=True)
                            break
                
                # Only add products that have both name and URL
                if product_info.get('name') and product_info.get('url'):
                    page_products.append(product_info)
            
            if page_products:
                all_products.extend(page_products)
                print(f"Found {len(page_products)} products on page {page_number}")
            else:
                print(f"No products found on page {page_number}")
            
            # Look for next page button
            next_button = None
            
            # Try different selectors for next button
            next_selectors = [
                'a[aria-label="Next"]',
                'a[title="Next"]',
                'a.next',
                '.next a'
            ]
            
            for selector in next_selectors:
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, selector)
                    if next_button and next_button.is_enabled():
                        break
                except NoSuchElementException:
                    continue
            
            # Try XPath selectors
            if not next_button:
                xpath_selectors = [
                    "//a[contains(text(), 'Next')]",
                    "//a[contains(text(), '>')]",
                    "//a[@aria-label='Next']",
                    f"//a[text()='{page_number + 1}']"
                ]
                
                for xpath in xpath_selectors:
                    try:
                        next_button = driver.find_element(By.XPATH, xpath)
                        if next_button and next_button.is_enabled():
                            break
                    except NoSuchElementException:
                        continue
            
            # Click next button if found
            if next_button:
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", next_button)
                    time.sleep(5)
                    
                    # Scroll to load content
                    for i in range(3):
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2)
                    
                    page_number += 1
                    
                    if page_number > 50:  # Safety limit
                        print("Reached maximum page limit, stopping...")
                        break
                        
                except Exception as e:
                    print(f"Error clicking next button: {e}")
                    break
            else:
                print("No more pages found")
                break
    
    except Exception as e:
        print(f"Error extracting products from collection: {e}")
    
    return all_products


def extract_product_details(driver, product_url, product_name):
    """Extract prices and sizes from individual product page with specific selectors"""
    print(f"  Extracting details for: {product_name}")
    
    try:
        driver.get(product_url)
        time.sleep(3)
        
        # Scroll to load content
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        product_details = {
            'name': product_name,
            'url': product_url,
            'size_price_combinations': []
        }
        
        # Get current page price from price__container (for reference)
        current_price = None
        try:
            price_container = driver.find_element(By.CSS_SELECTOR, '.price__container')
            raw_price = price_container.text.strip()
            current_price = format_price(raw_price)
            if current_price:
                print(f"    Current page price: {raw_price} → {current_price}")
        except NoSuchElementException:
            print("    No price__container found on current page")
        
        # Find size fieldset with class "js product-form__input"
        try:
            size_fieldset = driver.find_element(By.CSS_SELECTOR, 'fieldset.js.product-form__input')
            print("    Found size fieldset")
            
            # Find all labels within the fieldset
            size_labels = size_fieldset.find_elements(By.TAG_NAME, 'label')
            print(f"    Found {len(size_labels)} size labels")
            
            if size_labels:
                for i, label in enumerate(size_labels):
                    try:
                        # Get the size text
                        size_text = label.text.strip()
                        if not size_text:
                            # Try to get text from nested elements
                            size_text = label.get_attribute('textContent').strip()
                        
                        if "sample" in size_text.lower():
                            size_text = size_text.replace("sample", "").replace("Sample", "").strip()

                        # Filter out "sample" text and clean the size text
                        print(f"    Processing size: {size_text}")
                        
                        # Click the label to navigate to the size-specific page
                        driver.execute_script("arguments[0].scrollIntoView(true);", label)
                        time.sleep(1)
                        
                        # Click the label
                        driver.execute_script("arguments[0].click();", label)
                        time.sleep(3)  # Wait for page navigation/update
                        
                        # Get the price for this size from price__container
                        try:
                            price_container = driver.find_element(By.CSS_SELECTOR, '.price__container')
                            raw_price = price_container.text.strip()
                            formatted_price = format_price(raw_price)
                            
                            if formatted_price:
                                print(f"      Price for {size_text}: {raw_price} → {formatted_price}")
                                product_details['size_price_combinations'].append({
                                    'size': size_text,
                                    'price': formatted_price
                                })
                            else:
                                print(f"      Could not format price for {size_text}: {raw_price}")
                                
                        except NoSuchElementException:
                            print(f"      No price__container found for size {size_text}")
                        
                        # Small delay between size selections
                        time.sleep(1)
                            
                    except Exception as e:
                        print(f"    Error processing size label {i}: {e}")
                        continue
            else:
                print("    No size labels found in fieldset")
                
        except NoSuchElementException:
            print("    No size fieldset found, checking for single size product")
            
            # If no size fieldset, this might be a single-size product
            # Just get the current price
            if current_price:
                product_details['size_price_combinations'].append({
                    'size': 'Standard',
                    'price': current_price
                })
                print(f"    Single size product price: {current_price}")
            else:
                try:
                    price_container = driver.find_element(By.CSS_SELECTOR, '.price__container')
                    raw_price = price_container.text.strip()
                    formatted_price = format_price(raw_price)
                    if formatted_price:
                        product_details['size_price_combinations'].append({
                            'size': 'Standard',
                            'price': formatted_price
                        })
                        print(f"    Single size product price: {raw_price} → {formatted_price}")
                except NoSuchElementException:
                    print("    No price found for single size product")
        
        # Remove duplicate size-price combinations
        seen_combinations = set()
        unique_combinations = []
        for combo in product_details['size_price_combinations']:
            combo_key = (combo['size'], combo['price'])
            if combo_key not in seen_combinations:
                seen_combinations.add(combo_key)
                unique_combinations.append(combo)
        product_details['size_price_combinations'] = unique_combinations
        
        print(f"    Final: {len(product_details['size_price_combinations'])} size-price combinations")
        
        return product_details
    
    except Exception as e:
        print(f"    Error extracting details from {product_url}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'name': product_name,
            'url': product_url,
            'size_price_combinations': [],
            'error': str(e)
        }


def main():
    """Main scraping function"""
    collection_urls = [
        "https://www.rainshadowlabs.com/collections/hair-care",
        "https://www.rainshadowlabs.com/collections/cleansers"
    ]
    
    print("🚀 Starting enhanced product scraping...")
    print(f"Collection URLs: {len(collection_urls)} collections")
    for url in collection_urls:
        print(f"  - {url}")
    print("=" * 60)
    
    driver = setup_driver()
    
    try:
        all_detailed_products = []
        
        # Process each collection URL
        for collection_idx, collection_url in enumerate(collection_urls, 1):
            print(f"\n🏪 Collection {collection_idx}/{len(collection_urls)}: {collection_url}")
            print("-" * 60)
            
            # Step 1: Extract products from collection pages
            print("📋 Step 1: Extracting products from collection pages...")
            products = extract_products_from_collection(driver, collection_url)
            
            print(f"✅ Found {len(products)} products in this collection")
            
            if not products:
                print("❌ No products found in this collection. Skipping.")
                continue
            
            # Step 2: Extract details from each product page
            print(f"🔍 Step 2: Extracting details from {len(products)} product pages...")
            
            for i, product in enumerate(products, 1):
                print(f"\n[{i}/{len(products)}] Processing: {product['name']}")
                details = extract_product_details(driver, product['url'], product['name'])
                all_detailed_products.append(details)
                
                # Small delay to be respectful
                time.sleep(1)
        
        # Use all products from all collections
        detailed_products = all_detailed_products
        
        # Print summary
        print(f"\n📊 Summary:")
        print(f"   Total products processed: {len(detailed_products)}")
        
        products_with_combinations = sum(1 for p in detailed_products if p['size_price_combinations'])
        
        print(f"   Products with size-price combinations: {products_with_combinations}")
        
        # Show sample results
        print(f"\n🔍 Sample results:")
        for product in detailed_products[:3]:
            print(f"\n   {product['name']}")
            if product['size_price_combinations']:
                for combo in product['size_price_combinations'][:3]:
                    print(f"     {combo['size']}: {combo['price']}")
            else:
                print(f"     No size-price combinations found")
    
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.quit()
        print(f"\n🏁 Scraping completed!")


if __name__ == "__main__":
    main()