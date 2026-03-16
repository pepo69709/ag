import pandas as pd
import yfinance as yf
import numpy as np
import joblib
import config

print("🔍 【AI 本音調査：全銘柄ランキング・スカウター】")
print("AIが今、どの銘柄を『最もマシ』だと考えているか、TOP 10をあぶり出します。")

def calculate_metrics_raw(df, i):
    if i < 70: return None
    try:
        d = df.iloc[i-70:i+1]
        close = d['Close'].iloc[:, 0] if isinstance(d['Close'], pd.DataFrame) else d['Close']
        open_p = d['Open'].iloc[:, 0] if isinstance(d['Open'], pd.DataFrame) else d['Open']
        close = pd.to_numeric(close, errors='coerce').dropna()
        sma25 = close.rolling(window=25).mean()
        sma50 = close.rolling(window=50).mean()
        dev = (close / sma25 - 1) * 100
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss.replace(0, 1e-6)).fillna(0)))
        volat = close.pct_change().rolling(window=10).std() * np.sqrt(252) * 100
        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd_hist = (ema12 - ema26) - (ema12 - ema26).ewm(span=9).mean()
        return {
            "price": float(close.iloc[-1]), "dev": float(dev.iloc[-1]), "rsi": float(rsi.iloc[-1]),
            "trend": float((sma25/sma50).iloc[-1]), "macd": float(macd_hist.iloc[-1]),
            "volat": float(volat.iloc[-1]), "weekday": d.index[-1].weekday()
        }
    except: return None

model_xgb = joblib.load("xgb_model.pkl")
model_lgbm = joblib.load("lgbm_model.pkl")

tickers = config.WATCH_LIST[:200]
candidates = []

for ticker in tickers:
    try:
        data = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)
        if data.empty:
            print(f"Skipping {ticker}: Data empty")
            continue
        m = calculate_metrics_raw(data, len(data)-1)
        if not m:
            print(f"Skipping {ticker}: Metrics calculation failed")
            continue
        
        f_input = pd.DataFrame([{
            'feat_price': m['price'], 'feat_dev': m['dev'], 'feat_rsi': m['rsi'],
            'feat_vol': 1.0, 'feat_volatility': m['volat'], 
            'feat_trend': m['trend'], 'feat_dayofweek': m['weekday'],
            'feat_macd': m['macd'], 'feat_bb_pos': 0.0, 'feat_gap': 0.0,
            'feat_nikkei_trend': 2.0, 'feat_fear_index': 20.0, 'feat_market_phase': 1
        }])
        
        p_xgb = model_xgb.predict_proba(f_input)[0][1]
        p_lgbm = model_lgbm.predict_proba(f_input)[0][1]
        avg_p = (p_xgb + p_lgbm) / 2
        print(f"Found {ticker}: Prob {avg_p:.4f}")
        candidates.append({"ticker": ticker, "prob": avg_p, "price": m['price'], "dev": m['dev']})
    except Exception as e:
        print(f"Error on {ticker}: {e}")
        continue

df = pd.DataFrame(candidates).sort_values(by="prob", ascending=False)
print("\n🏆 【AIが選ぶ：今、最もリバウンドに近い銘柄 TOP 10】")
print(df.head(10).to_string(index=False))
