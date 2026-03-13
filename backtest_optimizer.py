import pandas as pd
import yfinance as yf
import numpy as np
import joblib
import os
from datetime import datetime
import config

print("🔍 黄金の境界線を探索中... (70% / 75% / 80% の各基準で勝率を比較します)")

def calculate_historical_features(df):
    close = df['Close']
    sma25 = close.rolling(window=25).mean()
    sma50 = close.rolling(window=50).mean()
    dev = (close / sma25 - 1) * 100
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi = 100 - (100 / (1 + (gain / loss.replace(0, 1e-6)).fillna(0)))
    vol_ratio = df['Volume'] / df['Volume'].rolling(window=20).mean()
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    macd_hist = macd - macd.ewm(span=9, adjust=False).mean()
    std25 = close.rolling(window=25).std()
    bb_pos = (close - sma25) / (std25 * 2) * 100
    gap = (df['Open'] / close.shift(1) - 1) * 100
    
    features = pd.DataFrame({
        'feat_price': close, 'feat_dev': dev, 'feat_rsi': rsi, 'feat_vol': vol_ratio,
        'feat_volatility': close.pct_change().rolling(window=10).std() * np.sqrt(252) * 100,
        'feat_trend': sma25 / sma50, 'feat_macd': macd_hist, 'feat_bb_pos': bb_pos, 'feat_gap': gap,
        'feat_dayofweek': df.index.dayofweek
    })
    return features.dropna()

def run_multi_backtest():
    try:
        xgb_model = joblib.load("xgb_model.pkl")
        lgbm_model = joblib.load("lgbm_model.pkl")
    except: return

    tickers = config.WATCH_LIST[:60] # 少し増やす
    thresholds = [0.70, 0.75, 0.80]
    results = {t: {"signals": 0, "wins": 0, "losses": 0} for t in thresholds}

    for ticker in tickers:
        try:
            data = yf.download(ticker, period="4mo", progress=False, auto_adjust=True)
            if data.empty: continue
            features = calculate_historical_features(data)
            
            for i in range(len(features) - 6):
                row = features.iloc[i]
                # 一致条件を少し緩和（DEV 3%からに）してデータを集める
                if not (3.0 <= row['feat_dev'] <= 25.0): continue
                
                f_input = pd.DataFrame([{
                    'feat_price': row['feat_price'], 'feat_dev': row['feat_dev'], 'feat_rsi': row['feat_rsi'],
                    'feat_vol': row['feat_vol'], 'feat_volatility': row['feat_volatility'], 
                    'feat_trend': row['feat_trend'], 'feat_dayofweek': row['feat_dayofweek'],
                    'feat_macd': row['feat_macd'], 'feat_bb_pos': row['feat_bb_pos'], 'feat_gap': row['feat_gap'],
                    'feat_nikkei_trend': 0.0, 'feat_fear_index': 20.0, 'feat_market_phase': 1.0
                }])
                
                avg_prob = (xgb_model.predict_proba(f_input)[0][1] + lgbm_model.predict_proba(f_input)[0][1]) / 2
                
                for th in thresholds:
                    if avg_prob >= th:
                        entry_price = data['Close'].iloc[i]
                        success = False
                        stop_out = False
                        for d in range(1, 6):
                            if ((data['High'].iloc[i+d] / entry_price) - 1) * 100 >= 1.0:
                                success = True; break
                            if ((data['Low'].iloc[i+d] / entry_price) - 1) * 100 <= -2.0:
                                stop_out = True; break
                        
                        results[th]["signals"] += 1
                        if success: results[th]["wins"] += 1
                        elif stop_out: results[th]["losses"] += 1
        except: continue

    print("\n🏆 【境界線探索・レポート】")
    for th in thresholds:
        sig = results[th]["signals"]
        win_rate = (results[th]["wins"] / sig * 100) if sig > 0 else 0
        print(f"🔹 基準 {int(th*100)}% ➔ 信号: {sig}回 / 推定勝率: {win_rate:.1f}%")

if __name__ == "__main__":
    run_multi_backtest()
