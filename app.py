import os
import json
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
import anthropic
import traceback

app = Flask(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
BASE_URL = "https://secure.cstorepro.com/EmagineNETCOSM"
USERNAME = "fifthstreet"
PASSWORD = "Volco@2604"

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
})

def login():
    try:
        print("Attempting login...")
        r = session.get(f"{BASE_URL}/login.aspx", timeout=15)
        print(f"Login page status: {r.status_code}")
        
        soup = BeautifulSoup(r.text, 'html.parser')
        
        vs = soup.find('input', {'name': '__VIEWSTATE'})
        ev = soup.find('input', {'name': '__EVENTVALIDATION'})
        
        payload = {
            '__VIEWSTATE': vs['value'] if vs else '',
            '__EVENTVALIDATION': ev['value'] if ev else '',
            'ctl00$MainContent$txtUserName': USERNAME,
            'ctl00$MainContent$txtPassword': PASSWORD,
            'ctl00$MainContent$btnLogin': 'Login'
        }
        
        r2 = session.post(f"{BASE_URL}/login.aspx", data=payload, timeout=15)
        print(f"After login URL: {r2.url}")
        print(f"Login status: {r2.status_code}")
        
        success = 'login' not in r2.url.lower()
        print(f"Login success: {success}")
        return success
        
    except Exception as e:
        print(f"Login error: {e}")
        print(traceback.format_exc())
        return False

def search_price(product_name):
    try:
        print(f"Searching for: {product_name}")
        
        # Convert to search term using Claude
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        ai = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=30,
            messages=[{"role": "user", "content": f"Convert to store search keyword (2-3 words uppercase): '{product_name}'\nReply with ONLY the keyword."}]
        )
        search_term = ai.content[0].text.strip()
        print(f"Search term: {search_term}")
        
        # Go to items page
        search_url = f"{BASE_URL}/Content/POSManagement/POSItemList.aspx?&enetFoundationMenuId=1607"
        r = session.get(search_url, timeout=15)
        print(f"Items page status: {r.status_code}, URL: {r.url}")
        
        # Check if still logged in
        if 'login' in r.url.lower():
            print("Session expired, logging in again...")
            login()
            r = session.get(search_url, timeout=15)
        
        # Search with term
        r2 = session.get(f"{search_url}&filter=ItemName&search={search_term}", timeout=15)
        print(f"Search results status: {r2.status_code}")
        
        html = r2.text[:5000]
        print(f"HTML snippet: {html[:500]}")
        
        # Extract price with Claude
        ai2 = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=200,
            messages=[{"role": "user", "content": f"""From this HTML find products matching "{search_term}" and prices.
Return ONLY JSON: {{"products": [{{"name": "name", "price": "$X.XX"}}]}}
If nothing: {{"products": []}}
HTML: {html}"""}]
        )
        
        result_text = ai2.content[0].text.strip()
        print(f"AI result: {result_text}")
        
        try:
            result = json.loads(result_text)
        except:
            result = {"products": []}
        
        return result.get("products", [])
        
    except Exception as e:
        print(f"Search error: {e}")
        print(traceback.format_exc())
        return []

# Login on startup
print("=== Starting Fifth St Food Mart Price Lookup ===")
login_success = login()
print(f"Startup login: {login_success}")

@app.route('/price', methods=['POST'])
def get_price():
    data = request.json
    product = data.get('product', '')
    print(f"\n=== Price lookup: {product} ===")
    
    if not product:
        return jsonify({"error": "No product"}), 400
    
    products = search_price(product)
    
    if products:
        if len(products) == 1:
            msg = f"{products[0]['name']} is {products[0]['price']}"
        else:
            msg = "We have: " + ", ".join([f"{p['name']} for {p['price']}" for p in products[:3]])
        return jsonify({"success": True, "message": msg})
    else:
        return jsonify({"success": False, "message": f"Sorry I could not find {product} in our store"})

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "running", "login": login_success})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
