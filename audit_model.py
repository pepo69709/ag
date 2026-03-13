import pandas as pd
import yfinance as yf
import numpy as np
import joblib
import os

def calculate_metrics_vectorized(df):
    # 強制的に1次元Seriesにする
    close = df['Close'].iloc[:, 0] if len(df['Close'].shape) > 1 else df['Close']
    open_p = df['Open'].iloc[:, 0] if len(df['Open'].shape) > 1 else df['Open']
    volume = df['Volume'].iloc[:, 0] if len(df['Volume'].shape) > 1 else df['Volume']
    
    sma25 = close.rolling(window=25).mean()
    sma50 = close.rolling(window=50).mean()
    dev = (close / sma25 - 1) * 100
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi = 100 - (100 / (1 + (gain / loss.replace(0, 1e-6)).fillna(0)))
    volatility = close.pct_change().rolling(window=10).std() * np.sqrt(252) * 100
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    macd_hist = macd - macd.ewm(span=9, adjust=False).mean()
    std25 = close.rolling(window=25).std()
    bb_pos = (close - sma25) / (std25 * 2) * 100
    gap = (open_p / close.shift(1) - 1) * 100
    
    features = pd.DataFrame({
        'feat_price': close, 'feat_dev': dev, 'feat_rsi': rsi,
        'feat_vol': volume / volume.rolling(window=20).mean(),
        'feat_volatility': volatility, 'feat_trend': sma25 / sma50,
        'feat_macd': macd_hist, 'feat_bb_pos': bb_pos, 'feat_gap': gap,
        'feat_dayofweek': df.index.dayofweek
    })
    return features.dropna()

def audit_ticker():
    try:
        xgb_model = joblib.load("xgb_model.pkl")
        lgbm_model = joblib.load("lgbm_model.pkl")
    except: return

    ticker = "1332.T" # 代表：ニッスイ
    data = yf.download(ticker, period="3mo", progress=False, auto_adjust=True)
    features = calculate_metrics_vectorized(data)
    
    print(f"📊 【{ticker}：AI本音全記録】")
    print("日付        | 終値   | 乖離率 | RSI  | AIスコア(%)")
    print("-" * 50)
    
    for i in range(len(features)):
        dt = features.index[i]
        row = features.iloc[i]
        
        f_input = pd.DataFrame([{
            'feat_price': row['feat_price'], 'feat_dev': row['feat_dev'], 'feat_rsi': row['feat_rsi'],
            'feat_vol': row['feat_vol'], 'feat_volatility': row['feat_volatility'], 
            'feat_trend': row['feat_trend'], 'feat_dayofweek': row['feat_dayofweek'],
            'feat_macd': row['feat_macd'], 'feat_bb_pos': row['feat_bb_pos'], 'feat_gap': row['feat_gap'],
            'feat_nikkei_trend': 5.0, 'feat_fear_index': 20.0, 'feat_market_phase': 2.0
        }])
        
        prob = (xgb_model.predict_proba(f_input)[0][1] + lgbm_model.predict_proba(f_input)[0][1]) / 2
        print(f"{dt.strftime('%Y-%m-%d')} | {row['feat_price']:6.1f} | {row['feat_dev']:6.2f} | {row['feat_rsi']:4.1f} | {prob*100:5.1f}%")

if __name__ == "__main__":
    audit_ticker()
