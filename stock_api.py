from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

def clean_key(text):
    """
    Cleans the label text (e.g., removes 'Impled Shares Outstanding' tooltip text
    if it gets caught in the grab).
    """
    # Remove any extra whitespace and newlines
    text = text.strip()
    # If the text has 'Shares Out', we might want to strip the tooltip text if it was grabbed.
    # But usually, get_text(strip=True) handles this reasonably well.
    return text

@app.route('/api/stock/<symbol>', methods=['GET'])
def get_stock_data(symbol):
    url = f"https://stockanalysis.com/stocks/{symbol}/"
    
    # Headers are crucial. Without a User-Agent, the site will likely return a 403 Forbidden.
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
        
        # Based on the HTML you provided, the data is inside <table> elements.
        # We find all tables and iterate through their rows.
        tables = soup.find_all('table')
        
        if not tables:
             return jsonify({"error": "No tables found on the page. The site structure may have changed."}), 404

        for table in tables:
            # Find all rows in the table
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                
                # We specifically look for rows with exactly 2 columns (Label + Value)
                if len(cols) == 2:
                    # Column 0 is the Label (e.g., Market Cap)
                    # We use .stripped_strings to separate the main text from tooltips/spans
                    # and take the first part.
                    label_parts = list(cols[0].stripped_strings)
                    label = label_parts[0] if label_parts else "Unknown"
                    
                    # Column 1 is the Value (e.g., 22.39M)
                    value = cols[1].get_text(strip=True)
                    
                    data[label] = value

        return jsonify({
            "symbol": symbol.upper(),
            "source": url,
            "data": data
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Running on port 5000
    app.run(debug=True, port=5000)