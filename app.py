from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
import time

app = Flask(__name__)

STORE_URL = "https://secure.cstorepro.com/EmagineNETCOSM"
USERNAME = "fifthstreet"
PASSWORD = "Volco@2604"

def get_price(product_name):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        )
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            page.goto(f"{STORE_URL}/login.aspx", timeout=30000)
            time.sleep(2)
            page.fill('input[name="ctl00$MainContent$txtUserName"]', USERNAME)
            page.fill('input[name="ctl00$MainContent$txtPassword"]', PASSWORD)
            page.click('input[type="submit"]')
            page.wait_for_load_state('networkidle', timeout=30000)
            time.sleep(2)

            page.goto(f"{STORE_URL}/Content/POSManagement/POSItemList.aspx?&enetFoundationMenuId=1607", timeout=30000)
            time.sleep(2)

            page.fill('input[placeholder="Search"]', product_name)
            page.keyboard.press('Enter')
            time.sleep(3)

            rows = page.locator('table tbody tr')
            if rows.count() == 0:
                browser.close()
                return {"success": False, "message": f"Sorry I could not find {product_name}"}

            item_name = rows.nth(0).locator('td').nth(1).text_content()
            rows.nth(0).locator('td').nth(1).click()
            time.sleep(2)

            price = page.locator('text=/\\$[0-9]+\\.[0-9]+/').first.text_content()
            browser.close()
            return {"success": True, "product": item_name.strip(), "price": price.strip(), "message": f"{item_name.strip()} costs {price.strip()}"}

        except Exception as e:
            browser.close()
            return {"success": False, "message": f"Sorry I had trouble finding that price"}

@app.route('/price', methods=['POST'])
def price():
    data = request.json
    product = data.get('product', '')
    if not product:
        return jsonify({"error": "No product name"}), 400
    result = get_price(product)
    return jsonify(result)

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "running"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
