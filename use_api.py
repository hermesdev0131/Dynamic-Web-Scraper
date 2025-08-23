import requests
import json

def fetch_hair_care_products():
    """
    Fetch all hair-care products from RainShadow Labs and save to JSON.
    Only includes: name, size, price
    """
    # base_url = "https://www.rainshadowlabs.com/collections/hair-care/products.json"
    base_url = "https://www.rainshadowlabs.com/collections/cleansers/products.json"
    all_products = []
    page = 1

    while True:
        response = requests.get(f"{base_url}?page={page}")
        if response.status_code != 200:
            print(f"Failed to fetch page {page}: Status code {response.status_code}")
            break

        data = response.json()
        products = data.get("products", [])

        if not products:
            print("No more products found, ending.")
            break

        for product in products:
            product_name = product.get("title", "Unnamed Product")

            for variant in product.get("variants", []):
                size = variant.get("title", "Default")
                size_clean = size.lower().replace("sample", "").strip()
                price = float(variant.get("price", 0))
                price_with_unit = f"${price:.2f}"
                all_products.append({
                    "name": product_name,
                    "size": size_clean,
                    "price": price_with_unit
                })

        print(f"Page {page} processed, collected {len(products)} products.")
        page += 1

    # Save to JSON file
    with open("hair_care_products.json", "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=4, ensure_ascii=False)

    print(f"Saved {len(all_products)} product variants to hair_care_products.json")

if __name__ == "__main__":
    fetch_hair_care_products()
