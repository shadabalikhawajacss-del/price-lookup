import os
import json
from flask import Flask, request, jsonify
import anthropic

app = Flask(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

PDI_USERNAME = "fifthstreet"
PDI_PASSWORD = "Volco@2604"
PDI_URL = "https://secure.cstorepro.com/EmagineNETCOSM"

def search_product_price(product_name: str) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Create Managed Agent session
    response = client.beta.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        betas=["managed-agents-2026-04-01"],
        tools=[{"type": "agent_toolset_20260401"}],
        system=f"""You are a price lookup assistant for Fifth St Food Mart.
Your job is to find the price of any product from the store's PDI system.

Store credentials:
- URL: {PDI_URL}/login.aspx
- Username: {PDI_USERNAME}
- Password: {PDI_PASSWORD}

Steps to find price:
1. Go to the login page and login
2. Navigate to Price Book → Items
3. Search for the product
4. Click the first matching result
5. Return the product name and price

Always return price in this format:
PRODUCT: [name]
PRICE: [price]""",
        messages=[{
            "role": "user",
            "content": f"Find the price of: {product_name}"
        }]
    )
    
    # Extract price from response
    result_text = ""
    for block in response.content:
        if hasattr(block, 'text'):
            result_text += block.text
    
    return {
        "success": True,
        "message": result_text,
        "raw": result_text
    }


@app.route('/price', methods=['POST'])
def get_price():
    data = request.json
    product = data.get('product', '')
    
    if not product:
        return jsonify({"error": "No product specified"}), 400
    
    print(f"Looking up: {product}")
    result = search_product_price(product)
    return jsonify(result)


@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "running", "store": "Fifth St Food Mart"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
