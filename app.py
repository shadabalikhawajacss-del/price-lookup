services:
  - type: web
    name: price-lookup
    env: python
    buildCommand: pip install -r requirements.txt && playwright install chromium && playwright install-deps chromium
    startCommand: python app.py
    plan: free
