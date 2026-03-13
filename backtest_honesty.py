import pandas as pd
import yfinance as yf
import numpy as np
import joblib
import os
import config

print("🔍 AIの『本音』を調査中... (50%〜70% の生の確信度でどれだけ勝てているか？)")

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

def run_honesty_test():
    try:
        xgb_model = joblib.load("xgb_model.pkl")
        lgbm_model = joblib.load("lgbm_model.pkl")
    except: return

    # 対象を絞って深く調査 (30銘柄)
    tickers = config.WATCH_LIST[:30]
    total_samples = 0
    results_list = []

    for ticker in tickers:
        try:
            data = yf.download(ticker, period="3mo", progress=False, auto_adjust=True)
            if data.empty: continue
            features = calculate_historical_features(data)
            
            for i in range(len(features) - 6):
                row = features.iloc[i]
                # 判定条件を極限まで緩和
                if not (2.0 <= row['feat_dev'] <= 30.0): continue
                
                f_input = pd.DataFrame([{
                    'feat_price': row['feat_price'], 'feat_dev': row['feat_dev'], 'feat_rsi': row['feat_rsi'],
                    'feat_vol': row['feat_vol'], 'feat_volatility': row['feat_volatility'], 
                    'feat_trend': row['feat_trend'], 'feat_dayofweek': row['feat_dayofweek'],
                    'feat_macd': row['feat_macd'], 'feat_bb_pos': row['feat_bb_pos'], 'feat_gap': row['feat_gap'],
                    'feat_nikkei_trend': 0.0, 'feat_fear_index': 20.0, 'feat_market_phase': 1.0
                }])
                
                avg_prob = (xgb_model.predict_proba(f_input)[0][1] + lgbm_model.predict_proba(f_input)[0][1]) / 2
                
                # 50%以上を一律記録
                if avg_prob >= 0.50:
                    entry_price = data['Close'].iloc[i]
                    success = False
                    for d in range(1, 6):
                        if ((data['High'].iloc[i+d] / entry_price) - 1) * 100 >= 1.0:
                            success = True; break
                        if ((data['Low'].iloc[i+d] / entry_price) - 1) * 100 <= -2.0:
                            break
                    results_list.append({"prob": avg_prob, "win": 1 if success else 0})
        except: continue

    df_res = pd.DataFrame(results_list)
    if df_res.empty:
        print("😱 50%以上の確信度すら見つかりません。モデルかデータの計算方法に根本的なズレがある可能性があります。")
        return

    print("\n🏆 【AI確信度 vs 1.0%達成率】")
    ranges = [(0.50, 0.55), (0.55, 0.60), (0.60, 0.65), (0.65, 0.70), (0.70, 1.0)]
    for r in ranges:
        target = df_res[(df_res['prob'] >= r[0]) & (df_res['prob'] < r[1])]
        if not target.empty:
            win_rate = target['win'].mean() * 100
            print(f"📊 AIスコア {int(r[0]*100)}%-{int(r[1]*100)}% ➔ サンプル:{len(target)}回 / 実際の勝率: {win_rate:.1f}%")

if __name__ == "__main__":
    run_honesty_test()
