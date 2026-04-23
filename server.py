from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__, static_folder='.')

PORTFOLIO_FILE = 'portfolio.csv'

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

@app.route('/api/record', methods=['POST'])
def record_trade():
    try:
        data = request.json
        # ticker, entry_price, quantity, status, entry_date
        new_row = {
            "ticker": data['ticker'],
            "entry_price": float(data['price']),
            "quantity": int(data['quantity']),
            "status": "HOLD",
            "entry_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        df = pd.read_csv(PORTFOLIO_FILE)
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(PORTFOLIO_FILE, index=False)
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/sell', methods=['POST'])
def sell_trade():
    try:
        data = request.json
        ticker = data['ticker']
        df = pd.read_csv(PORTFOLIO_FILE)
        df = df[df['ticker'] != ticker]
        df.to_csv(PORTFOLIO_FILE, index=False)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    print("🏹 Sniper AI: Portfolio Backend starting at http://localhost:5000")
    app.run(port=5000, debug=True)
