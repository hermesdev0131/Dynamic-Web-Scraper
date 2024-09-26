from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from scraper import fetch_data, extract_data

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
        
        # Extract paragraphs and titles
        data = extract_data(soup)
        
        # Return the extracted data as JSON
        return {"data": data}
    except Exception as e:
        # Return a 500 error if scraping fails
        raise HTTPException(status_code=500, detail=f'An error occurred: {str(e)}')
