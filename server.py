from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import os
import json
import glob
from datetime import datetime
import numpy as np
import yfinance as yf
import pickle
import threading
import time
from indicators import Indicators
from strategy_core import get_signal
from execution_engine import ExecutionEngine
from risk_engine import RiskEngine

TICKERS = [
    '8035.T', '6920.T', '6146.T', '6857.T', '4063.T', '6501.T',
    '6702.T', '6723.T', '6752.T', '6758.T', '6981.T', '6902.T',
    '6954.T', '7733.T', '7741.T', '6971.T', '7203.T', '7267.T',
    '7269.T', '7201.T', '7261.T', '7270.T', '7272.T', '7011.T',
    '7012.T', '8306.T', '8316.T', '8411.T', '8766.T', '8725.T',
    '8604.T', '8750.T', '7182.T', '8001.T', '8002.T', '8031.T',
    '8053.T', '8058.T', '5020.T', '5019.T', '9984.T', '9432.T',
    '9433.T', '9434.T', '4689.T', '3659.T', '4755.T', '9983.T',
    '8267.T', '7974.T', '2413.T', '3382.T', '4502.T', '4503.T',
    '4519.T', '4568.T', '4507.T', '6367.T', '6301.T', '6326.T',
    '7832.T', '6113.T', '4183.T', '4188.T', '4204.T', '3407.T',
    '5401.T', '5406.T', '8802.T', '8801.T', '8830.T', '1928.T',
    '1925.T', '2802.T', '2503.T', '2587.T', '2269.T', '6098.T',
    '4661.T', '9602.T', '9201.T', '1458.T', '1459.T', '1357.T'
]

app = Flask(__name__, static_folder='.')
CORS(app)

class SniperBrain:
    def __init__(self):
        try:
            with open('models/model_lgbm.pkl', 'rb') as f: self.lgbm = pickle.load(f)
            with open('models/model_clf.pkl',  'rb') as f: self.clf  = pickle.load(f)
            with open('models/feature_cols.pkl', 'rb') as f: self.feature_cols = pickle.load(f)
            print('[SUCCESS] Brain V9.8.3 (Auto-Patrol) Loaded.')
        except: self.lgbm = self.clf = None

    def predict_ev(self, df, mkt_trend, fx_roc, mkt_vol):
        if self.lgbm is None: return 0.0, 0, 0, 0, 0.5
        c = df['Close']
        p = float(c.iloc[-1])
        rsi = Indicators.rsi(df).iloc[-1]
        ml, ms = Indicators.macd(df)
        bu, bm, bl = Indicators.bbands(df)
        atr, adx = Indicators.atr(df).iloc[-1], Indicators.adx(df).iloc[-1]
        s20, s50, s200 = c.rolling(20).mean().iloc[-1], c.rolling(50).mean().iloc[-1], c.rolling(200).mean().iloc[-1]
        v20 = df['Volume'].rolling(20).mean().iloc[-1]
        h250 = df['High'].rolling(250).max().iloc[-1]
        f_dict = {
            'RSI': rsi, 'MACD': ml.iloc[-1], 'MACD_Signal': ms.iloc[-1],
            'BB_Upper': bu.iloc[-1], 'BB_Mid': bm.iloc[-1], 'BB_Lower': bl.iloc[-1],
            'ATR': atr, 'ADX': adx, 'SMA_20': s20, 'SMA_50': s50, 'SMA_200': s200,
            'kairi_20': (p/s20-1)*100, 'kairi_200': (p/s200-1)*100, 'vol_ratio': float(df['Volume'].iloc[-1])/(v20+1e-9),
            'return_lag_1': c.pct_change(1).iloc[-1]*100, 'rsi_lag_1': Indicators.rsi(df).iloc[-2],
            'return_lag_2': c.pct_change(1).iloc[-2]*100, 'rsi_lag_2': Indicators.rsi(df).iloc[-3],
            'return_lag_3': c.pct_change(1).iloc[-2]*100, 'rsi_lag_3': Indicators.rsi(df).iloc[-4],
            'high_52w_ratio': p/(h250+1e-9), 'roc_20': c.pct_change(20).iloc[-1]*100,
            'bb_position': (p-bl.iloc[-1])/(bu.iloc[-1]-bl.iloc[-1]+1e-9),
            'atr_compression': Indicators.atr(df,7).iloc[-1]/Indicators.atr(df,30).iloc[-1],
            'vol_trend': df['Volume'].rolling(5).mean().iloc[-1]/(v20+1e-9),
            'mkt_trend': mkt_trend, 'fx_roc': fx_roc, 'mkt_vol': mkt_vol
        }
        X = pd.DataFrame([f_dict])[self.feature_cols]
        ev = float(self.lgbm.predict(X)[0])
        prob = float(self.clf.predict_proba(X)[0][1])
        threshold = 0.60 if mkt_vol > 2.0 else 0.55
        return ev, (1 if prob >= threshold else 0), p, (Indicators.atr(df).iloc[-1]/p*100*2.236), prob

brain = SniperBrain()

def run_scan_internal():
    try:
        ts = datetime.now().strftime('%H:%M:%S')
        print(f"[AUTO] {ts} 定時スキャン開始...")
        n = yf.download('^N225', period='1mo', progress=False)
        j = yf.download('JPY=X', period='1mo', progress=False)
        if isinstance(n.columns, pd.MultiIndex): n.columns = n.columns.get_level_values(0)
        if isinstance(j.columns, pd.MultiIndex): j.columns = j.columns.get_level_values(0)
        mt = (n['Close'].iloc[-1]/n['Close'].rolling(20).mean().iloc[-1]-1)*100
        fr = j['Close'].pct_change(5).iloc[-1]*100
        mv = (Indicators.atr(n).iloc[-1]/n['Close'].iloc[-1])*100
        
        rows = []
        log_rows = []
        now = datetime.now().isoformat()
        for t in TICKERS:
            d = yf.download(t, period='2y', progress=False)
            if d.empty or len(d)<250: continue
            if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
            ev, win, p, rng, pb = brain.predict_ev(d, mt, fr, mv)
            v = Indicators.get_pattern_score(d)
            threshold = 0.60 if mv > 2.0 else 0.55
            is_s = (get_signal(d) and pb >= threshold and p <= 15000 and v >= 65)
            
            rows.append({
                'ticker':t, 'price':p, 'score':0.88 if is_s else 0.32, 'win_prob':win,
                'pattern_score':v, 'mechanical_rule':'🎯 STRONG' if is_s else '⏳ WAIT',
                'true_ev':round(ev*100,2), 'expected_range':round(rng,2), 'target_price':round(p*(1+ev),1),
                'analysis': f'Prob:{round(pb*100,1)}%'
            })
            log_rows.append({
                'timestamp': now, 'ticker': t, 'price': p, 'ai_prob': pb, 'ai_ev': ev,
                'mkt_vol': mv, 'mkt_trend': mt, 'fx_roc': fr, 'is_strong': 1 if is_s else 0
            })
            
        pd.DataFrame(rows).to_csv('database.csv', index=False)
        log_file = 'prediction_audit_log.csv'
        log_df = pd.DataFrame(log_rows)
        if os.path.exists(log_file): log_df.to_csv(log_file, mode='a', header=False, index=False)
        else: log_df.to_csv(log_file, index=False)
        print(f"[AUTO] {ts} スキャン完了。")
    except Exception as e: print(f"[ERROR] Auto scan failed: {e}")

def auto_scan_loop():
    while True:
        run_scan_internal()
        print("[AUTO] 次回スキャンまで1時間待機します...")
        time.sleep(3600)

@app.route('/')
def index(): return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path): return send_from_directory('.', path)

@app.route('/api/refresh', methods=['POST'])
def refresh():
    threading.Thread(target=run_scan_internal).start()
    return jsonify({'status':'processing'})

if __name__ == '__main__':
    threading.Thread(target=auto_scan_loop, daemon=True).start()
    app.run(port=5000)