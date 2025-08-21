#!/usr/bin/env python3
"""
Flask server for web scraping that can be triggered by n8n
Receives requests, runs scraping, and returns JSON data
"""

from flask import Flask, request, jsonify
import json
import time
import threading
from datetime import datetime
import logging
import os
import sys

# Import our scraping functions
from scraper import (
    setup_driver, 
    extract_products_from_collection, 
    extract_product_details,
    format_price
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    # handlers=[
    #     logging.FileHandler('/home/hermes/Documents/work/Dynamic-Web-Scraper/scraper_server.log'),
    #     logging.StreamHandler(sys.stdout)
    # ]
)

app = Flask(__name__)

# Global variable to track scraping status
scraping_status = {
    'is_running': False,
    'last_run': None,
    'last_result': None,
    'error': None
}



@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'scraping_status': {
            'is_running': scraping_status['is_running'],
            'last_run': scraping_status['last_run']
        }
    })

@app.route('/scrape', methods=['POST'])
def scrape():
    """Main scraping endpoint for n8n - runs scraping and returns results"""
    
    # Check if scraping is already running
    if scraping_status['is_running']:
        return jsonify({
            'error': 'Scraping is already in progress',
            'status': 'running'
        }), 409
    
    try:
        # Get collection URLs from request (optional)
        data = request.get_json() if request.is_json else {}
        
        # Default collection URLs
        default_urls = [
            "https://www.rainshadowlabs.com/collections/hair-care"
            # "https://www.rainshadowlabs.com/collections/cleansers"
        ]
        
        collection_urls = data.get('collection_urls', default_urls)
        
        # Validate URLs
        if not isinstance(collection_urls, list) or not collection_urls:
            return jsonify({
                'error': 'Invalid collection_urls. Must be a non-empty list of URLs.'
            }), 400
        
        logging.info(f"Received synchronous scraping request for {len(collection_urls)} collections")
        
        # Run scraping synchronously
        scraping_status['is_running'] = True
        scraping_status['error'] = None
        
        driver = setup_driver()
        all_detailed_products = []
        
        try:
            # Process each collection URL
            for collection_idx, collection_url in enumerate(collection_urls, 1):
                logging.info(f"Processing collection {collection_idx}/{len(collection_urls)}: {collection_url}")
                
                # Extract products from collection pages
                products = extract_products_from_collection(driver, collection_url)
                logging.info(f"Found {len(products)} products in collection")
                
                if not products:
                    logging.warning(f"No products found in collection: {collection_url}")
                    continue
                
                # Extract details from each product page
                for i, product in enumerate(products, 1):
                    logging.info(f"Processing product {i}/{len(products)}: {product['name']}")
                    details = extract_product_details(driver, product['url'], product['name'])
                    all_detailed_products.append(details)
                    
                    # Small delay to be respectful
                    time.sleep(1)
            
            # Prepare final result
            result = {
                'collection_urls': collection_urls,
                'total_collections': len(collection_urls),
                'total_products': len(all_detailed_products),
                'scraped_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'products': all_detailed_products,
                'status': 'completed'
            }
            
            scraping_status['last_result'] = result
            scraping_status['last_run'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            logging.info(f"Synchronous scraping completed successfully. Total products: {len(all_detailed_products)}")
            
            return jsonify(result)
            
        finally:
            driver.quit()
            scraping_status['is_running'] = False
            
    except Exception as e:
        error_msg = f"Scraping failed: {str(e)}"
        logging.error(error_msg)
        scraping_status['is_running'] = False
        return jsonify({'error': error_msg, 'status': 'failed'}), 500



@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("🚀 Starting Scraper Server...")
    print("Available endpoints:")
    print("  GET  /health    - Health check")
    print("  POST /scrape    - Run scraping and return results (for n8n)")
    print("\nServer starting on http://0.0.0.0:5000")
    print("=" * 60)
    
    # Run the Flask server
    app.run(
        host='0.0.0.0',  # Listen on all interfaces
        port=5000,
        debug=False,     # Set to False for production
        threaded=True    # Enable threading for concurrent requests
    )