import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import datetime
import json

def is_valid_url(url, base_domain):
    """Check if the URL is valid and belongs to the same domain."""
    parsed = urlparse(url)
    return bool(parsed.netloc) and parsed.netloc == base_domain

def crawl_for_product_urls(start_url, max_pages=100):
    base_domain = urlparse(start_url).netloc
    visited = set()
    queue = deque([(start_url, 0)])  # (url, depth)
    product_urls = set()

    while queue and len(visited) < max_pages:
        url, depth = queue.popleft()
        
        if url in visited:
            continue
        
        print(f"Crawling: {url}")
        visited.add(url)
        
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all links on the page
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(url, href)
                
                if '/products/' in full_url and is_valid_url(full_url, base_domain):
                    product_urls.add(full_url)
                elif is_valid_url(full_url, base_domain) and full_url not in visited:
                    queue.append((full_url, depth + 1))
        
        except Exception as e:
            print(f"Error crawling {url}: {e}")

    return list(product_urls)

def get_page_reviews(driver):
    """Fetch and parse review data from the current page."""
    review_elements = driver.find_elements(By.CLASS_NAME, 'jdgm-rev')
    reviews = []
    for element in review_elements:
        try:
            author = element.find_element(By.CLASS_NAME, 'jdgm-rev__author').text.strip()
        except:
            author = "Unknown"

        try:
            stars = element.find_element(By.CLASS_NAME, 'jdgm-rev__rating').get_attribute('data-score')
        except:
            stars = "Not found"

        try:
            date_element = element.find_element(By.CLASS_NAME, 'jdgm-rev__timestamp')
            timestamp = date_element.get_attribute('data-content')
        except:
            timestamp = "Not found"

        try:
            body = element.find_element(By.CLASS_NAME, 'jdgm-rev__body').text.strip()
        except:
            body = "No review text"

        reviews.append({
            "author": author,
            "stars": stars,
            "timestamp": timestamp,
            "body": body
        })
    return reviews

def scrape_product_info(url):
    """Scrape product name and price."""
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    try:
        product_name = soup.find('div', {'class': 'product__title'}).get_text(strip=True)
    except:
        product_name = "Product name not found"

    try:
        price = soup.find('span', {'class': 'price-item price-item--sale price-item--last'}).get_text(strip=True)
    except:
        price = "Price not found"

    return product_name, price

def get_last_page(driver):
    """Determine the last page number from the pagination element."""
    pagination = driver.find_elements(By.CLASS_NAME, 'jdgm-paginate__page')
    if not pagination:
        return 1  # No pagination means only one page
    
    # Extract the maximum page number from the pagination links
    pages = [int(page.get_attribute('data-page')) for page in pagination if page.get_attribute('data-page')]
    
    return max(pages, default=1)

def scrape_all_reviews(url, driver):
    """Scrape all reviews from all pages."""
    driver.get(url)

    try:
        # Wait for the reviews to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'jdgm-rev__body'))
        )
    except:
        print(f"No reviews found for {url}")
        return []

    last_page = get_last_page(driver)
    all_reviews = []

    for page in range(1, last_page + 1):
        reviews = get_page_reviews(driver)
        all_reviews.extend(reviews)
        print(f"Scraped page {page} of {last_page}")

        if page < last_page:
            try:
                # Click the next page button
                next_button = driver.find_element(By.CSS_SELECTOR, f'a.jdgm-paginate__page[data-page="{page + 1}"]')
                driver.execute_script("arguments[0].click();", next_button)
                
                # Wait for the new reviews to load
                time.sleep(2)  # You might need to adjust this delay
            except:
                print(f"Couldn't load more reviews after page {page}")
                break

    return all_reviews

def main():
    start_url = 'https://villagecompanystore.com'
    product_urls = crawl_for_product_urls(start_url)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    all_product_data = []

    for url in product_urls:
        print(f"\nProcessing: {url}")
        
        # Scrape reviews
        reviews = scrape_all_reviews(url, driver)
        
        # Scrape product info
        product_name, price = scrape_product_info(url)

        product_data = {
            "url": url,
            "product_name": product_name,
            "price": price,
            "total_reviews": len(reviews),
            "reviews": reviews
        }

        all_product_data.append(product_data)

        print(f"Product Name: {product_name}")
        print(f"Price: {price}")
        print(f"Total Reviews Found: {len(reviews)}")

    driver.quit()

    # Save all data to a JSON file
    with open('product_data.json', 'w', encoding='utf-8') as f:
        json.dump(all_product_data, f, ensure_ascii=False, indent=4)

    print("\nAll data has been saved to product_data.json")

if __name__ == "__main__":
    main()