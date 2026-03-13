import pandas as pd
import yfinance as yf
import numpy as np
import joblib
import os
import config

print("🛡️ 【真実の最終検証：日経平均連動モード】")

def calculate_metrics_vectorized(df):
    close = df['Close']
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
    gap = (df['Open'] / close.shift(1) - 1) * 100
    
    features = pd.DataFrame({
        'feat_price': close, 'feat_dev': dev, 'feat_rsi': rsi,
        'feat_vol': df['Volume'] / df['Volume'].rolling(window=20).mean(),
        'feat_volatility': volatility, 'feat_trend': sma25 / sma50,
        'feat_macd': macd_hist, 'feat_bb_pos': bb_pos, 'feat_gap': gap,
        'feat_dayofweek': df.index.dayofweek
    })
    return features.dropna()

def run_final_backtest():
    try:
        xgb_model = joblib.load("xgb_model.pkl")
        lgbm_model = joblib.load("lgbm_model.pkl")
    except:
        print("❌ モデルが読み込めません。")
        return

    # 日経平均の歴史を取得
    print("🌍 日経平均の歴史をロード中...")
    nikkei = yf.download("^N225", period="6mo", progress=False, auto_adjust=True)
    n_close = nikkei['Close']
    n_trend_series = (n_close / n_close.shift(20) - 1) * 100
    n_vol_series = n_close.pct_change().rolling(window=20).std() * np.sqrt(252) * 100

    # 対象銘柄
    tickers = config.WATCH_LIST[:40] 
    results = []

    for ticker in tickers:
        try:
            data = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)
            if data.empty: continue
            features = calculate_metrics_vectorized(data)
            
            for i in range(len(features) - 6):
                dt = features.index[i]
                if dt not in n_trend_series.index: continue
                
                row = features.iloc[i]
                # 日経のマクロ指標を当時の日付から取得
                n_t = n_trend_series.loc[dt]
                n_v = n_vol_series.loc[dt]
                n_p = 2 if n_t > 3 else (0 if n_t < -3 else 1)
                
                # AI入力
                f_input = pd.DataFrame([{
                    'feat_price': row['feat_price'], 'feat_dev': row['feat_dev'], 'feat_rsi': row['feat_rsi'],
                    'feat_vol': row['feat_vol'], 'feat_volatility': row['feat_volatility'], 
                    'feat_trend': row['feat_trend'], 'feat_dayofweek': row['feat_dayofweek'],
                    'feat_macd': row['feat_macd'], 'feat_bb_pos': row['feat_bb_pos'], 'feat_gap': row['feat_gap'],
                    'feat_nikkei_trend': n_t, 'feat_fear_index': n_v, 'feat_market_phase': n_p
                }])
                
                avg_prob = (xgb_model.predict_proba(f_input)[0][1] + lgbm_model.predict_proba(f_input)[0][1]) / 2
                
                # 調査のため、55%以上をすべて記録
                if avg_prob >= 0.55:
                    entry_p = data['Close'].iloc[i]
                    success = False
                    for d in range(1, 6):
                        if ((data['High'].iloc[i+d] / entry_p) - 1) * 100 >= 1.0:
                            success = True; break
                        if ((data['Low'].iloc[i+d] / entry_p) - 1) * 100 <= -2.0:
                            break
                    results.append({"prob": avg_prob, "win": 1 if success else 0})
        except: continue

    df_res = pd.DataFrame(results)
    if df_res.empty:
        print("⚠️ それでも信号が出ませんでした。AIの判定基準が極めて特殊か、学習データと現在の計算ロジックに剥離があります。")
        return

    print("\n📊 【AIスコア別・的中率（+1.0%目標）】")
    for th in [0.55, 0.60, 0.65, 0.70, 0.75]:
        target = df_res[df_res['prob'] >= th]
        if not target.empty:
            print(f"🔹 スコア {int(th*100)}%以上 ➔ 成功率: {target['win'].mean()*100:.1f}% ({len(target)}回検知)")

if __name__ == "__main__":
    run_final_backtest()
