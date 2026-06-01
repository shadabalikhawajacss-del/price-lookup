from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
import os

app = Flask(__name__)

STORE_URL = "https://secure.cstorepro.com/EmagineNETCOSM"
USERNAME = "fifthstreet"
PASSWORD = "Volco@2604"

def get_product_price(product_name):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Login
            page.goto(f"{STORE_URL}/login.aspx")
            page.fill('input[name="ctl00$MainContent$txtUserName"]', USERNAME)
            page.fill('input[name="ctl00$MainContent$txtPassword"]', PASSWORD)
            page.click('input[value="Login"]')
            page.wait_for_load_state('networkidle')
            
            # Go to items page
            page.goto(f"{STORE_URL}/Content/POSManagement/POSItemList.aspx?&enetFoundationMenuId=1607")
            page.wait_for_load_state('networkidle')
            
            # Search product
            page.fill('input[placeholder="Search"]', product_name)
            page.keyboard.press('Enter')
            page.wait_for_load_state('networkidle')
            
            # Click first result
            first_item = page.locator('table tr td').nth(1)
            item_name = first_item.text_content()
            first_item.click()
            page.wait_for_load_state('networkidle')
            
            # Get price
            price = page.locator('//*[contains(text(),"$")]').first.text_content()
            
            browser.close()
            return {"success": True, "product": item_name, "price": price}
            
        except Exception as e:
            browser.close()
            return {"success": False, "error": str(e)}

@app.route('/price', methods=['POST'])
def price():
    data = request.json
    product = data.get('product', '')
    if not product:
        return jsonify({"error": "No product name"}), 400
    result = get_product_price(product)
    return jsonify(result)

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "running"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
