from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from scraper import fetch_data, extract_data, extract_all_data, scrape_all_pages
import time

app = FastAPI()

# A simple homepage endpoint
@app.get('/')
def home():
    return {'data': 'Welcome to the Web Scraper API!'}

# Request schema for the scraper
class ScraperRequest(BaseModel):
    url: HttpUrl

# The endpoint to accept URLs and return scraped data
@app.post('/scrape')
def scrape_data(request: ScraperRequest):
    try:
        # Use Selenium to fetch the page content
        soup = fetch_data(str(request.url))
        
        # Extract paragraphs and titles (basic extraction)
        data = extract_data(soup)
        
        # Return the extracted data as JSON
        return {"data": data}
    except Exception as e:
        # Return a 500 error if scraping fails
        raise HTTPException(status_code=500, detail=f'An error occurred: {str(e)}')

# Enhanced endpoint for e-commerce product scraping
@app.post('/scrape-products')
def scrape_products(request: ScraperRequest):
    try:
        # Use Selenium to fetch the page content
        soup = fetch_data(str(request.url))
        
        # Extract all data including products
        data = extract_all_data(soup)
        
        # Return the extracted data as JSON
        return {"data": data}
    except Exception as e:
        # Return a 500 error if scraping fails
        raise HTTPException(status_code=500, detail=f'An error occurred: {str(e)}')

# Multi-page scraping endpoint
@app.post('/scrape-all-pages')
def scrape_all_pages_endpoint(request: ScraperRequest):
    try:
        # Scrape all pages with pagination
        all_products = scrape_all_pages(str(request.url))
        
        # Prepare response data
        response_data = {
            "url": str(request.url),
            "total_products": len(all_products),
            "scraping_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "products": all_products
        }
        
        # Return the extracted data as JSON
        return {"data": response_data}
    except Exception as e:
        # Return a 500 error if scraping fails
        raise HTTPException(status_code=500, detail=f'An error occurred: {str(e)}')
