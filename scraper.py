# Import libraries
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time

# Fetch data from the dynamic page
def fetch_data(url):
    # Headless Chrome for performance
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # Open URL
        driver.get(url)

        # Wait for the page to fully load
        time.sleep(5)  # You can adjust this depending on the page load time

        # Scroll down to load more content if needed
        for i in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

        # Get the fully rendered page source
        page_source = driver.page_source
    finally:
        driver.quit()

    # Parse HTML using BeautifulSoup
    soup = BeautifulSoup(page_source, 'html.parser')
    return soup

# Extract paragraphs and titles
def extract_data(soup):
    # Fetch paragraphs and titles
    paragraphs = [para.get_text(strip=True) for para in soup.find_all('p')]
    titles = [title.get_text(strip=True) for title in soup.find_all(['h1', 'h2', 'h3'])]

    # Filter out common unwanted content
    unwanted_phrases = ['CONNECT WITH US', 'BACK TO TOP', 'Copyright']
    cleaned_paragraphs = [
        para for para in paragraphs if not any(unwanted in para for unwanted in unwanted_phrases)
    ]

    return {
        "titles": titles,
        "paragraphs": cleaned_paragraphs
    }
