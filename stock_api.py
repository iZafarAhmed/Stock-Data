from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
import traceback

app = Flask(__name__)

# Basic route to check if the server is actually running
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "online",
        "message": "Stock API is running. Use /api/stock/<symbol> to get data."
    })

@app.route('/api/stock/<symbol>', methods=['GET'])
def get_stock_data(symbol):
    # Data source URL
    url = f"https://stockanalysis.com/stocks/{symbol}/"
    
    # Headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            return jsonify({
                "error": "Failed to fetch data from source", 
                "status_code": response.status_code
            }), 502

        soup = BeautifulSoup(response.content, 'html.parser')
        
        data = {}
        
        # Find tables
        tables = soup.find_all('table')
        
        if not tables:
             return jsonify({"error": "No tables found on the page. The site structure may have changed."}), 404

        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                
                # Look for Label + Value pairs
                if len(cols) == 2:
                    # Extract Label
                    label_parts = list(cols[0].stripped_strings)
                    label = label_parts[0] if label_parts else "Unknown"
                    
                    # Extract Value
                    value = cols[1].get_text(strip=True)
                    
                    data[label] = value

        return jsonify({
            "symbol": symbol.upper(),
            "source": url,
            "data": data
        })

    except Exception as e:
        # Return full traceback in the error to help debugging
        return jsonify({
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500

# Vercel looks for 'app', so this is sufficient.
if __name__ == '__main__':
    app.run(debug=True, port=5000)
