import pandas as pd
import yfinance as yf
import numpy as np
import joblib
from datetime import datetime, timedelta
import config

print("🌋 【AI タイムマシン・ストレス・テスト：異なる相場環境での的中率】")

def calculate_metrics_safe(df, i):
    if i < 70: return None
    try:
        d = df.iloc[i-70 : i+1]
        close = d['Close'].iloc[:, 0] if isinstance(d['Close'], pd.DataFrame) else d['Close']
        close = pd.to_numeric(close).dropna()
        sma25 = close.rolling(window=25).mean()
        sma50 = close.rolling(window=50).mean()
        dev = (close / sma25 - 1) * 100
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss.replace(0, 1e-6)).fillna(0)))
        volat = close.pct_change().rolling(window=10).std() * np.sqrt(252) * 100
        macd = (close.ewm(span=12).mean() - close.ewm(span=26).mean())
        macd_hist = macd - macd.ewm(span=9).mean()
        return {
            "price": float(close.iloc[-1]), "dev": float(dev.iloc[-1]), "rsi": float(rsi.iloc[-1]),
            "trend": float((sma25/sma50).iloc[-1]), "macd": float(macd_hist.iloc[-1]),
            "volat": float(volat.iloc[-1]), "weekday": d.index[-1].weekday()
        }
    except: return None

# Load models
model_xgb = joblib.load("xgb_model.pkl")
model_lgbm = joblib.load("lgbm_model.pkl")

# 検証ターゲット（歴史的時期）
test_scenarios = [
    {"name": "2024年8月暴落期 (Panic)", "date": "2024-08-06"},
    {"name": "2024年11月上昇期 (Bull)", "date": "2024-11-12"},
    {"name": "2025年5月停滞期 (Flat)", "date": "2025-05-15"},
    {"name": "直近 2026年2月 (Recent)", "date": "2026-02-25"}
]

tickers = config.WATCH_LIST[:50] # 50銘柄でサンプリング

for scenario in test_scenarios:
    print(f"\n--- 🛰️ ターゲット: {scenario['name']} [{scenario['date']}] ---")
    results = []
    
    for ticker in tickers:
        try:
            # 各時期に合わせて長めのデータを取得
            start_date = (datetime.strptime(scenario['date'], '%Y-%m-%d') - timedelta(days=150)).strftime('%Y-%m-%d')
            end_date = (datetime.strptime(scenario['date'], '%Y-%m-%d') + timedelta(days=20)).strftime('%Y-%m-%d')
            data = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
            if data.empty: continue
            
            idx_list = data.index.strftime('%Y-%m-%d').tolist()
            if scenario['date'] not in idx_list:
                available = [d for d in idx_list if d <= scenario['date']]
                if not available: continue
                current_date_str = available[-1]
            else:
                current_date_str = scenario['date']
            
            c_idx = idx_list.index(current_date_str)
            m = calculate_metrics_safe(data, c_idx)
            if not m: continue
            
            f_input = pd.DataFrame([{
                'feat_price': m['price'], 'feat_dev': m['dev'], 'feat_rsi': m['rsi'],
                'feat_vol': 1.0, 'feat_volatility': m['volat'], 
                'feat_trend': m['trend'], 'feat_dayofweek': m['weekday'],
                'feat_macd': m['macd'], 'feat_bb_pos': 0.0, 'feat_gap': 0.0,
                'feat_nikkei_trend': 0.0, 'feat_fear_index': 20.0, 'feat_market_phase': 1
            }])
            
            prob = (model_xgb.predict_proba(f_input)[0][1] + model_lgbm.predict_proba(f_input)[0][1]) / 2
            
            # 5日間の結果確認
            e_p = float(data['Close'].iloc[c_idx].item()) if hasattr(data['Close'].iloc[c_idx], 'item') else float(data['Close'].iloc[c_idx])
            win = 0
            for d in range(1, 6):
                if c_idx + d >= len(data): break
                hi = float(data['High'].iloc[c_idx+d].item()) if hasattr(data['High'].iloc[c_idx+d], 'item') else float(data['High'].iloc[c_idx+d])
                lo = float(data['Low'].iloc[c_idx+d].item()) if hasattr(data['Low'].iloc[c_idx+d], 'item') else float(data['Low'].iloc[c_idx+d])
                if ((hi / e_p) - 1) * 100 >= 1.0: win = 1; break
                if ((lo / e_p) - 1) * 100 <= -2.0: break
            
            results.append({"ticker": ticker, "prob": prob, "win": win})
        except: continue
    
    if results:
        df_res = pd.DataFrame(results).sort_values(by="prob", ascending=False)
        top_5 = df_res.head(5)
        wr = top_5['win'].mean() * 100
        print(f"📊 TOP 5 的中率: {wr:.1f}%")
        print(top_5[['ticker', 'prob', 'win']].to_string(index=False))
    else:
        print("❌ データ不足のためスキップ")

print("\n💡 結論: 上記全ての期間で的中率が高ければ、AIは将来の未知の相場でも通用する『汎化性能』を持っています。")
