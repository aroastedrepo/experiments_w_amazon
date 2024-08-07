from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import json

import requests
from bs4 import BeautifulSoup
import json
import time

'''
    Scrapes product URLs from an Amazon search results page.

    This function sends a GET request to the specified Amazon search URL,
    parses the HTML content using Beautiful Soup, and extracts product URLs
    from the search results page.

    Args:
    url (str): The URL of the Amazon search results page to scrape.

    Returns:
    list: A list of strings, where each string is a full URL to a product page.
          Returns an empty list if an error occurs during the request or parsing.
'''
def get_product_urls(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    product_urls = []

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        soup = BeautifulSoup(response.content, 'html.parser')

        product_cards = soup.find_all('div', {'data-component-type': 's-search-result'})

        for card in product_cards:
            a_tag = card.find('a', class_='a-link-normal s-no-outline')
            if a_tag and 'href' in a_tag.attrs:
                product_url = 'https://www.amazon.in' + a_tag['href']
                product_urls.append(product_url)

        return product_urls

    except requests.RequestException as e:
        print(f"An error occurred while fetching the page: {e}")
        return []

search_url = "https://www.amazon.in/s?i=merchant-items&me=A1PFJQPY00GT61&fs=true&ref=lp_27943762031_sar"
product_urls = get_product_urls(search_url)

print(f"Total products found: {len(product_urls)}")
for url in product_urls:
    print(url)

# Save product URLs to a JSON file
with open('product_urls.json', 'w', encoding='utf-8') as f:
    json.dump(product_urls, f, ensure_ascii=False, indent=4)

print("'product_urls.json' configured")

'''
"""
    Scrapes customer reviews from an Amazon product page.

    This function uses Selenium to navigate through multiple pages of reviews
    for a given Amazon product. It extracts the reviewer's name, rating, and
    review text from each review on the page.

    Args:
    base_url (str): The base URL of the Amazon product page to scrape reviews from.

    Returns:
    list: A list of dictionaries, where each dictionary contains information
          about a single review with the following keys:
          - 'name': The name of the reviewer (str)
          - 'rating': The rating given by the reviewer (str)
          - 'review': The text content of the review (str)

    Behavior:
    - Navigates through paginated review pages until no more reviews are found.
    - Scrolls down each page to ensure all reviews are loaded.
    - Implements waits between actions to allow for page loading.
    - Prints progress information to the console.
'''
def scrape_amazon_reviews(base_url):
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    all_reviews = []
    page_number = 1

    try:
        while True:
            url_parts = base_url.split("ref=", 1)
            if len(url_parts) == 2:
                url = f"{url_parts[0]}ref=cm_cr_arp_d_paging_btm_next_{page_number}?ie=UTF8&reviewerType=all_reviews&pageNumber={page_number}"
            else:
                url = f"{base_url}ref=cm_cr_arp_d_paging_btm_next_{page_number}?ie=UTF8&reviewerType=all_reviews&pageNumber={page_number}"

            driver.get(url)
            time.sleep(5)  # Wait for page to load

            # Scroll down the page to load all reviews
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            review_containers = soup.find_all('div', {'data-hook': 'review'})

            if not review_containers:
                print(f"No reviews found on page {page_number}. Stopping.")
                break

            for container in review_containers:
                name_element = container.find('span', class_='a-profile-name')
                name = name_element.text if name_element else 'Unknown'

                rating_element = container.find('i', class_='a-icon-star')
                rating = rating_element.text.strip() if rating_element else 'No rating'

                review_body = container.find('span', {'data-hook': 'review-body'})
                review_text = review_body.text.strip() if review_body else 'No review text'

                all_reviews.append({
                    'name': name,
                    'rating': rating,
                    'review': review_text
                })

            print(f"Scraped page {page_number}, Total reviews so far: {len(all_reviews)}")

            # Check for the next page button
            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'li.a-last'))
                )
                if 'a-disabled' in next_button.get_attribute('class'):
                    print("Reached the last page.")
                    break
                next_button.find_element(By.TAG_NAME, 'a').click()
                page_number += 1
                time.sleep(5)  # Increased wait time for next page to load
            except (NoSuchElementException, TimeoutException):
                print("No more pages found.")
                break

        return all_reviews

    finally:
        driver.quit()

search_url = "https://www.amazon.in/s?i=merchant-items&me=A1PFJQPY00GT61&fs=true&ref=lp_27943762031_sar"

all_product_reviews = {}

# For all product URLs in the list, scrape Amazon reviews individually per URL.
for url in product_urls:
    print(f"Scraping reviews for product: {url}")
    product_reviews = scrape_amazon_reviews(url)
    all_product_reviews[url] = product_reviews

    print(f"Total reviews scraped for this product: {len(product_reviews)}")
    print("-" * 50)

# Save all reviews to a JSON file
with open('all_amazon_reviews.json', 'w', encoding='utf-8') as f:
    json.dump(all_product_reviews, f, ensure_ascii=False, indent=4)

print("All reviews have been saved to 'all_amazon_reviews.json'")