import os
import json
import time
from flask import Flask, request, jsonify
import anthropic
from steel import Steel
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# API Keys from environment variables
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
STEEL_API_KEY = os.environ.get("STEEL_API_KEY")

# PDI Store credentials
PDI_URL = "https://secure.cstorepro.com/EmagineNETCOSM/login.aspx"
PDI_USERNAME = "fifthstreet"
PDI_PASSWORD = "Volco@2604"

def search_product_price(product_name: str) -> dict:
    steel_client = Steel(steel_api_key=STEEL_API_KEY)
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Step 1: Use Claude AI to convert customer words to search term
    ai_response = anthropic_client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=50,
        messages=[{
            "role": "user",
            "content": f"""Convert this to a store search keyword (2-3 words, uppercase):
Customer said: "{product_name}"
Examples:
- "bud light six pack" -> "BUD LIGHT 6"
- "corona beer" -> "CORONA"
- "marlboro" -> "MARLBORO"
- "red bull" -> "RED BULL"
- "extra gum" -> "EXTRA GUM"
- "doritos chips" -> "DORITOS"
Reply with ONLY the search keyword."""
        }]
    )
    search_term = ai_response.content[0].text.strip()
    print(f"Search term: {search_term}")

    # Step 2: Create Steel browser session
    session = steel_client.sessions.create(solve_captcha=True)
    print(f"Steel session: {session.id}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(
                f"wss://connect.steel.dev?apiKey={STEEL_API_KEY}&sessionId={session.id}"
            )
            context = browser.contexts[0]
            page = context.new_page()

            # Login to PDI store
            page.goto(PDI_URL, wait_until='networkidle', timeout=30000)
            time.sleep(2)
            page.fill('input[name="ctl00$MainContent$txtUserName"]', PDI_USERNAME)
            page.fill('input[name="ctl00$MainContent$txtPassword"]', PDI_PASSWORD)
            page.click('input[type="submit"]')
            page.wait_for_load_state('networkidle', timeout=30000)
            time.sleep(2)

            # Go to items page
            page.goto(
                "https://secure.cstorepro.com/EmagineNETCOSM/Content/POSManagement/POSItemList.aspx?&enetFoundationMenuId=1607",
                wait_until='networkidle',
                timeout=30000
            )
            time.sleep(2)

            # Search for product
            page.fill('input[placeholder="Search"]', search_term)
            page.keyboard.press('Enter')
            time.sleep(3)

            # Get page content
            page_content = page.content()
            browser.close()

        steel_client.sessions.release(session.id)

        # Step 3: Use Claude AI to extract price from results
        price_response = anthropic_client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": f"""From this HTML, find products matching "{search_term}" and their prices.
Return ONLY this JSON format:
{{"products": [{{"name": "product name", "price": "$X.XX"}}]}}
If nothing found: {{"products": []}}
HTML: {page_content[:8000]}"""
            }]
        )

        result_text = price_response.content[0].text.strip()
        try:
            result = json.loads(result_text)
        except:
            result = {"products": []}

        return {
            "success": True,
            "search_term": search_term,
            "products": result.get("products", [])
        }

    except Exception as e:
        steel_client.sessions.release(session.id)
        return {"success": False, "error": str(e), "products": []}


@app.route('/price', methods=['POST'])
def get_price():
    data = request.json
    product = data.get('product', '')
    if not product:
        return jsonify({"error": "No product specified"}), 400

    print(f"Looking up price for: {product}")
    result = search_product_price(product)

    if result["success"] and result["products"]:
        products = result["products"]
        if len(products) == 1:
            msg = f"{products[0]['name']} is {products[0]['price']}"
        else:
            msg = "We have: " + ", ".join([f"{p['name']} for {p['price']}" for p in products[:3]])
        return jsonify({"success": True, "message": msg, "products": products})
    else:
        return jsonify({"success": False, "message": f"Sorry I could not find {product} in our store"})


@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "running", "store": "Fifth St Food Mart"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
