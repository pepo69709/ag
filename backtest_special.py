import pandas as pd
import yfinance as yf
import numpy as np
import joblib
import os
import config

print("🔍 【AI 本領発揮テスト：得意の価格帯で勝負】")

def calculate_metrics_vectorized(df):
    close = df['Close']
    sma25 = close.rolling(window=25).mean()
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
        'feat_volatility': volatility, 'feat_trend': sma25 / close.rolling(window=50).mean(),
        'feat_macd': macd_hist, 'feat_bb_pos': bb_pos, 'feat_gap': gap,
        'feat_dayofweek': df.index.dayofweek
    })
    return features.dropna()

def run_expert_backtest():
    try:
        xgb_model = joblib.load("xgb_model.pkl")
        lgbm_model = joblib.load("lgbm_model.pkl")
    except: return

    # AIが得意な価格帯（300円〜2000円）の銘柄をピックアップ
    # 例：1332.T(ニッスイ), 1802.T(大林組), 2337.T(いちご), 2503.T(キリン), 5406.T(神戸鋼)
    target_tickers = ['1332.T', '1802.T', '1803.T', '2337.T', '2503.T', '3101.T', '3402.T', '4005.T', '5406.T', '6302.T', '6752.T', '6753.T', '7201.T', '7211.T', '8306.T', '8411.T', '9501.T', '9502.T', '9503.T']
    
    results = []

    for ticker in target_tickers:
        try:
            data = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)
            if data.empty: continue
            features = calculate_metrics_vectorized(data)
            
            for i in range(len(features) - 6):
                row = features.iloc[i]
                
                f_input = pd.DataFrame([{
                    'feat_price': row['feat_price'], 'feat_dev': row['feat_dev'], 'feat_rsi': row['feat_rsi'],
                    'feat_vol': row['feat_vol'], 'feat_volatility': row['feat_volatility'], 
                    'feat_trend': row['feat_trend'], 'feat_dayofweek': row['feat_dayofweek'],
                    'feat_macd': row['feat_macd'], 'feat_bb_pos': row['feat_bb_pos'], 'feat_gap': row['feat_gap'],
                    'feat_nikkei_trend': 5.0, 'feat_fear_index': 20.0, 'feat_market_phase': 2.0 # 好調な相場と仮定
                }])
                
                avg_prob = (xgb_model.predict_proba(f_input)[0][1] + lgbm_model.predict_proba(f_input)[0][1]) / 2
                
                # 70%以上を抽出
                if avg_prob >= 0.70:
                    entry_p = data['Close'].iloc[i]
                    success = False
                    for d in range(1, 6):
                        if ((data['High'].iloc[i+d] / entry_p) - 1) * 100 >= 1.0:
                            success = True; break
                        if ((data['Low'].iloc[i+p] / entry_p) - 1) * 100 <= -2.0:
                            break
                    results.append({"ticker": ticker, "prob": avg_prob, "win": 1 if success else 0})
        except: continue

    df_res = pd.DataFrame(results)
    if df_res.empty:
        print("⚠️ 合格銘柄がまだありません。市場全体の相関を見直します。")
        return

    print("\n📊 【AI得意銘柄限定：的中率レポート（+1.0%目線）】")
    for th in [0.70, 0.75, 0.80]:
        target = df_res[df_res['prob'] >= th]
        if not target.empty:
            print(f"🔹 スコア {int(th*100)}%以上 ➔ 平均勝率: {target['win'].mean()*100:.1f}% ({len(target)}回検知)")

if __name__ == "__main__":
    run_expert_backtest()
