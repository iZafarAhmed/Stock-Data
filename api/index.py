from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
import traceback
import re

app = Flask(__name__)

# Headers to mimic a real browser (Critical for scraping)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "online",
        "endpoints": {
            "price_data": "/api/stock/<symbol>",
            "company_profile": "/api/stock/<symbol>/profile"
        }
    })

# --- ENDPOINT 1: PRICE DATA (Existing) ---
@app.route('/api/stock/<symbol>', methods=['GET'])
def get_stock_data(symbol):
    url = f"https://stockanalysis.com/stocks/{symbol}/"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch data", "code": response.status_code}), 502

        soup = BeautifulSoup(response.content, 'html.parser')
        data = {}
        
        # Basic table scraping
        tables = soup.find_all('table')
        for table in tables:
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) == 2:
                    label = list(cols[0].stripped_strings)[0] if list(cols[0].stripped_strings) else "Unknown"
                    value = cols[1].get_text(strip=True)
                    data[label] = value

        return jsonify({"symbol": symbol.upper(), "data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- ENDPOINT 2: COMPANY PROFILE (New) ---
@app.route('/api/stock/<symbol>/profile', methods=['GET'])
def get_profile_data(symbol):
    url = f"https://stockanalysis.com/stocks/{symbol}/company/"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch profile", "code": response.status_code}), 502

        soup = BeautifulSoup(response.content, 'html.parser')
        profile = {
            "symbol": symbol.upper(),
            "description": "",
            "stock_details": {},
            "contact": {},
            "executives": []
        }

        # 1. Get Company Description
        # Looks for <h1>Company Description</h1> and gets the text from the next <div>
        desc_header = soup.find('h1', string=re.compile('Company Description'))
        if desc_header:
            desc_div = desc_header.find_next_sibling('div')
            if desc_div:
                # Join all paragraphs with a space
                profile['description'] = " ".join([p.get_text(strip=True) for p in desc_div.find_all('p')])

        # 2. Helper to process key-value tables
        def process_kv_table(header_text):
            data_dict = {}
            # Find the header (h2)
            header = soup.find('h2', string=re.compile(header_text))
            if header:
                # The table is usually in the next sibling div
                container = header.find_next_sibling('div')
                if container:
                    table = container.find('table')
                    if table:
                        for row in table.find_all('tr'):
                            cols = row.find_all('td')
                            # Handle Standard Rows (Label | Value)
                            if len(cols) == 2:
                                key = cols[0].get_text(strip=True)
                                val = cols[1].get_text(strip=True)
                                data_dict[key] = val
                            # Handle "Address" which is often a colspan=2 with a div inside
                            elif len(cols) == 1 and 'colspan' in cols[0].attrs:
                                text = cols[0].get_text(" ", strip=True) # Join lines with space
                                if "Address:" in text:
                                    data_dict['Address'] = text.replace("Address:", "").strip()
            return data_dict

        # 3. Fetch Stock Details & Contact Details
        profile['stock_details'] = process_kv_table("Stock Details")
        profile['contact'] = process_kv_table("Contact Details")

        # 4. Fetch Key Executives (Different table structure)
        exec_header = soup.find('h2', string=re.compile("Key Executives"))
        if exec_header:
            exec_table = exec_header.find_next_sibling('table')
            if exec_table:
                # Skip header row, iterate body
                rows = exec_table.find_all('tr')[1:] 
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        name = cols[0].get_text(strip=True)
                        title = cols[1].get_text(strip=True)
                        profile['executives'].append({"name": name, "title": title})

        return jsonify(profile)

    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
