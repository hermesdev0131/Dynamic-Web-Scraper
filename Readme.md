# Dynamic Web Scraper API

## Technologies Used
- **Python**: Core programming language for backend logic.
- **FastAPI**: For building a RESTful web API.
- **Selenium**:For rendering dynamic web pages with JavaScript.
- **BeautifulSoup**:  For parsing and extracting data from HTML.
- **Uvicorn**: ASGI server for running FastAPI apps.
- **Swagger UI** and **Postman**: For testing and validating API requests and responses.

---

## Table of Contents
1. [Project Description](#project-description)
2. [Key Features](#key-features)
3. [Types of Websites We Can Scrape](#types-of-websites-we-can-scrape)
4. [Installation](#installation)
5. [How to Use](#how-to-use)
6. [License](#license)

---

## Project Description

- The **Dynamic Web Scraper API** is a dynamic tool that allows users to extract content from web pages. Unlike traditional scrapers that rely on static HTML, this API handles dynamic websites (those with JavaScript-rendered content) using Selenium WebDriver for rendering and BeautifulSoup for parsing the fully rendered HTML.

- It offers an easy-to-use API for fetching web content without requiring the user to manually inspect HTML elements. Simply provide the URL of the page, and the API returns titles and paragraphs in structured JSON format.

---

## Key Features
- **Dynamic Content Handling:**  Capable of scraping websites that use JavaScript to render content dynamically.
- **Headless Browser Automation:**Utilizes Selenium WebDriver to render pages in a headless Chrome browser for improved performance.
- **API-based Scraping:** The API accepts a POST request with the URL and returns JSON-formatted content.
- **Error Handling:** Comprehensive error messages when issues occur during page loading or scraping.
- **Flexible Parsing:** Extracts paragraphs, headings, and filters out unwanted text (e.g., "Copyright" or "Terms").

---

## Types of Websites We Can Scrape
This scraper works well with websites that use JavaScript to render content, such as:
- **News Websites:**  Scrape articles, headlines, and publication dates.
- **E-commerce Sites:**  Extract product details, descriptions, and prices.
- **Dynamic Content:**  Websites where data is rendered dynamically via JavaScript, such as social media feeds, live scores, etc.

## Installation

1. Clone the repository:
   ```bash
   https://github.com/Abhimanyu-Gaurav/Dynamic-Web-Scraper-API

2. Navigate to the project directory:
   ```bash
   cd Dynamic-web-scraper-api

3. Set up a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`

4. Install the required dependencies:
   ```bash
   pip install -r requirements.txt

---

## How to Use

1. Run the FastAPI server:
   ```bash
   uvicorn main:app --reload


2. Open your browser (Safari, Chrome, Brave) and enter the URL:
   ```bash
   http://localhost:8000/docs#

3. This should display the Swagger UI for your FastAPI application.

4. Test the /scrape endpoint directly from the Swagger UI to ensure it is working and accessible.

5. Use the POST method (/scrape) and provide a JSON in the body like this:
    - Click on the "Try it out" button.
    - Provide a JSON in the request body:
    ```json
    {
        "url": "https://timesofindia.indiatimes.com/"
    }

6. Click on the "Execute" button to send the request.

7. You should see the scraped data in the response section if the request is successful.
   

### Send a POST request using API clients:
1. Using Postman:
    - Open Postman and click the "New" button to create a new request.
    - Set the request type to POST from the dropdown menu next to the URL field.
    - Enter the URL in the URL field:
      ```bash
      http://localhost:8000/scrape/

    -  Go to the "Body" tab.
        - Select the "raw" option and choose "JSON" from the dropdown.
        - Paste the following JSON into the body:
        ```json
        {
            "url": "https://timesofindia.indiatimes.com/"
        }

    - Click the "Send" button to execute the request.
    - You should see the scraped data in the response section if the request is successful. 

2. Using cURL:
- Open your terminal and run:
    ```bash
    curl -X POST "http://localhost:8000/scrape/" -H "Content-Type: application/json" -d '{"url": "https://timesofindia.indiatimes.com/"}'
    
- search: The term you want to search (e.g., business name or type).
- total: The number of listings to retrieve (if available).

---    

## License

- This project is licensed under the MIT License - see the [License](License) file for details.

---