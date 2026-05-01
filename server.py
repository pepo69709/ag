from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import os
import json
import glob
from datetime import datetime
import numpy as np
import yfinance as yf
from strategy_core import get_signal
from execution_engine import ExecutionEngine

# -------------------------------------------------
# 【精鋭 10 銘柄】クラウド Sniper と完全同期
# -------------------------------------------------
TICKERS = ["6857.T", "6146.T", "8035.T", "8058.T", "4063.T", "8306.T", "9432.T", "8411.T", "8802.T", "4503.T"]

app = Flask(__name__, static_folder='.')
CORS(app)

def load_latest_database():
    if os.path.exists("database.csv"):
        df = pd.read_csv("database.csv")
        return df[df['ticker'].isin(TICKERS)]
    return pd.DataFrame()

portfolio_path = "portfolio.json"
positions_file = "positions.json"
log_file = "trade_log.csv"
engine = ExecutionEngine(positions_file, log_file)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

@app.route('/api/refresh', methods=['POST'])
def refresh_live_data():
    """V110.0: [完全同期] クラウド Sniper と同じ脳(strategy_core)で更新"""
    try:
        updated_rows = []
        for ticker in TICKERS:
            print(f"[*] Cloud Sync: {ticker}...")
            data = yf.download(ticker, period="5d", interval="60m", progress=False)
            if data.empty: continue
            
            # 共通の脳(strategy_core)で判定
            match = get_signal(data)
            
            current_price = float(data['Close'].iloc[-1]) if not data.empty else 0
            score = 0.88 if match else 0.32
            
            updated_rows.append({
                'ticker': ticker,
                'price': current_price,
                'score': score,
                'confidence': 90.0 if match else 30.0,
                'pattern_score': 85.0 if match else 40.0,
                'mechanical_rule': '🎯 STRONG ENTRY' if match else '⏳ WAIT',
                'true_ev': None,
                'kelly_size': None,
                'signal_timestamp': datetime.now().isoformat(),
                'regime': 'SCANNING',
                'stars': '⭐⭐⭐⭐⭐' if match else '---',
                'analysis': 'Strategic Match' if match else 'Waiting...',
                'volatility': 0.012,
                'stop_loss': round(current_price * 0.98, 1)
            })
            
        new_db = pd.DataFrame(updated_rows)
        new_db.to_csv("database.csv", index=False)
        return jsonify({"status": "success", "message": "Unified Sync Complete"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/record', methods=['POST'])
def record_trade():
    try:
        data = request.json
        positions = engine.load_positions()
        if not any(p['ticker'] == data['ticker'] for p in positions):
            positions.append({
                "ticker": data['ticker'],
                "entry_price": float(data['price']),
                "entry_date": datetime.now().strftime("%Y-%m-%d"),
                "entry_ev": data.get('true_ev', 0),
                "entry_win_prob": data.get('win_prob', 0),
                "note": data.get('note', "")
            })
            engine.save_positions(positions)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    if os.path.exists(portfolio_path):
        with open(portfolio_path, "r") as f:
            portfolio = json.load(f)
    elif os.path.exists("portfolio.csv"):
        df = pd.read_csv("portfolio.csv")
        portfolio = df.to_dict(orient='records')
    else:
        portfolio = []
    db = load_latest_database()
    if not db.empty:
        current_prices = dict(zip(db['ticker'], db['price']))
        engine.check_exits(current_prices)
    return jsonify(portfolio)

@app.route('/api/performance', methods=['GET'])
def get_performance():
    if not os.path.exists(log_file): return jsonify({"ic": 0, "equity": [], "hit_rate": 0, "status": "No Data"})
    df = pd.read_csv(log_file)
    return jsonify({"ic": 0.1, "equity": df['pnl_rate'].cumsum().tolist() if 'pnl_rate' in df else [], "hit_rate": 55.0})

@app.route('/api/recalc', methods=['POST'])
def recalc_ev():
    try:
        import math
        data = request.json
        ticker = data['ticker']
        live_price = float(data['live_price'])
        db = load_latest_database()
        row = db[db['ticker'] == ticker]
        if row.empty: return jsonify({"status": "error", "message": "Ticker not found"}), 404
        row = row.iloc[0]
        signal_price = float(row['price'])
        signal_ev = 0.02
        volatility = 0.012
        signal_ts = datetime.fromisoformat(row['signal_timestamp'])
        elapsed_mins = (datetime.now() - signal_ts).total_seconds() / 60
        decay_ratio = elapsed_mins / 30
        time_decay = max(0.3, math.exp(-decay_ratio))
        target_price = signal_price * (1 + signal_ev * time_decay)
        new_ev = (target_price - live_price) / live_price
        price_gap = (live_price - signal_price) / signal_price
        if price_gap > 0.02: verdict = "🚫 TOO LATE"
        elif new_ev > (volatility * 1.5): verdict = "✅ GO"
        else: verdict = "⏳ WAIT"
        return jsonify({"status": "success", "ticker": ticker, "live_price": live_price, "new_ev": round(new_ev * 100, 3), "time_decay": round(time_decay, 2), "gap": round(price_gap * 100, 2), "verdict": verdict})
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    print("Sniper AI: Cloud Mirror Backend starting at http://localhost:5000")
    app.run(port=5000, debug=True)
