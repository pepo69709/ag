import pandas as pd
import yfinance as yf
import numpy as np
import joblib
from datetime import datetime
import config

print("🔍 【1332.T 深層調査：AIの思考プロセスを可視化】")

def calculate_metrics_for_test(df, i):
    if i < 70: return None
    try:
        d = df.iloc[i-70:i+1]
        close = d['Close'].iloc[:, 0] if len(d['Close'].shape) > 1 else d['Close']
        open_p = d['Open'].iloc[:, 0] if len(d['Open'].shape) > 1 else d['Open']
        
        close = pd.to_numeric(close, errors='coerce').dropna()
        sma25 = close.rolling(window=25).mean()
        sma50 = close.rolling(window=50).mean()
        dev = (close / sma25 - 1) * 100
        
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss.replace(0, 1e-6)).fillna(0)))
        
        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd_hist = (ema12 - ema26) - (ema12 - ema26).ewm(span=9).mean()
        
        return {
            "price": float(close.iloc[-1]), "dev": float(dev.iloc[-1]), "rsi": float(rsi.iloc[-1]),
            "trend": float((sma25/sma50).iloc[-1]), "macd": float(macd_hist.iloc[-1]),
            "weekday": d.index[-1].weekday()
        }
    except: return None

# Load model
model = joblib.load("xgb_model.pkl")

# Data fetch
ticker = "1332.T"
data = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)

print(f"Index | Price | Dev | RSI | Trend | MACD | AI Prob")
print("-" * 60)

for i in range(70, len(data)):
    m = calculate_metrics_for_test(data, i)
    if not m: continue
    
    # ダミーのマクロ指標
    f_input = pd.DataFrame([{
        'feat_price': m['price'], 'feat_dev': m['dev'], 'feat_rsi': m['rsi'],
        'feat_vol': 1.0, 'feat_volatility': 15.0, 
        'feat_trend': m['trend'], 'feat_dayofweek': m['weekday'],
        'feat_macd': m['macd'], 'feat_bb_pos': 0.0, 'feat_gap': 0.0,
        'feat_nikkei_trend': 2.0, 'feat_fear_index': 20.0, 'feat_market_phase': 1
    }])
    
    prob = model.predict_proba(f_input)[0][1]
    print(f"{data.index[i].strftime('%m/%d')} | {m['price']:6.1f} | {m['dev']:5.2f} | {m['rsi']:5.2f} | {m['trend']:5.3f} | {m['macd']:6.2f} | {prob:.4f}")

