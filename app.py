import os
import json
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
import anthropic

app = Flask(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
BASE_URL = "https://secure.cstorepro.com/EmagineNETCOSM"
USERNAME = "fifthstreet"
PASSWORD = "Volco@2604"

# Persistent session
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
})

def login():
    try:
        r = session.get(f"{BASE_URL}/login.aspx", timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        payload = {
            '__VIEWSTATE': soup.find('input', {'name': '__VIEWSTATE'})['value'] if soup.find('input', {'name': '__VIEWSTATE'}) else '',
            '__EVENTVALIDATION': soup.find('input', {'name': '__EVENTVALIDATION'})['value'] if soup.find('input', {'name': '__EVENTVALIDATION'}) else '',
            '__VIEWSTATEGENERATOR': soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value'] if soup.find('input', {'name': '__VIEWSTATEGENERATOR'}) else '',
            'ctl00$MainContent$txtUserName': USERNAME,
            'ctl00$MainContent$txtPassword': PASSWORD,
            'ctl00$MainContent$btnLogin': 'Login'
        }
        
        r2 = session.post(f"{BASE_URL}/login.aspx", data=payload, timeout=15)
        return 'TaskDashboard' in r2.url or 'Dashboard' in r2.text
    except Exception as e:
        print(f"Login error: {e}")
        return False

def search_price(product_name):
    try:
        # Use Claude AI to convert product name to search term
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        ai = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=30,
            messages=[{"role": "user", "content": f"Convert to store search keyword (2-3 words uppercase only): '{product_name}'\nReply with ONLY the keyword."}]
        )
        search_term = ai.content[0].text.strip()
        print(f"Search term: {search_term}")
        
        # Search items
        search_url = f"{BASE_URL}/Content/POSManagement/POSItemList.aspx?&enetFoundationMenuId=1607"
        r = session.get(search_url, timeout=15)
        
        if 'login' in r.url.lower():
            print("Session expired, logging in...")
            login()
            r = session.get(search_url, timeout=15)
        
        # Post search
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Find search form and submit
        r2 = session.get(
            f"{search_url}&filter=ItemName&search={search_term}",
            timeout=15
        )
        
        soup2 = BeautifulSoup(r2.text, 'html.parser')
        
        # Use Claude to extract price from HTML
        html_snippet = str(soup2)[:8000]
        
        ai2 = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=200,
            messages=[{"role": "user", "content": f"""From this HTML, find products matching "{search_term}" and their prices.
Return ONLY JSON: {{"products": [{{"name": "product name", "price": "$X.XX"}}]}}
If nothing found: {{"products": []}}
HTML: {html_snippet}"""}]
        )
        
        result_text = ai2.content[0].text.strip()
        try:
            result = json.loads(result_text)
        except:
            result = {"products": []}
        
        return result.get("products", [])
        
    except Exception as e:
        print(f"Search error: {e}")
        return []

# Login on startup
print("Logging into PDI store...")
login()
print("Login complete!")

@app.route('/price', methods=['POST'])
def get_price():
    data = request.json
    product = data.get('product', '')
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
        return jsonify({"success": False, "message": f"Sorry I could not find {product}"})

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "running"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
