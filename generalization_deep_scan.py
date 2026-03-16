import pandas as pd
import yfinance as yf
import numpy as np
import joblib
import os
import config

print("🛡️ 【真実の汎化性能・ディープスキャン】")
print("AIの確信度（70%/75%/80%/85%）ごとに、実際の+1.0%的中率を算出します。")

def calculate_metrics_for_test(df, i):
    if i < 50: return None
    try:
        d = df.iloc[i-50:i+1]
        close = d['Close'].iloc[:, 0] if len(d['Close'].shape) > 1 else d['Close']
        open_p = d['Open'].iloc[:, 0] if len(d['Open'].shape) > 1 else d['Open']
        volume = d['Volume'].iloc[:, 0] if len(d['Volume'].shape) > 1 else d['Volume']
        
        sma25 = close.rolling(window=25).mean()
        dev = (close / sma25 - 1) * 100
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss.replace(0, 1e-6)).fillna(0)))
        vol_ratio = volume / volume.rolling(window=20).mean()
        volatility = close.pct_change().rolling(window=10).std() * np.sqrt(252) * 100
        sma50 = close.rolling(window=50).mean()
        trend_sma = (sma25 / sma50)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = (ema12 - ema26) - (ema12 - ema26).ewm(span=9, adjust=False).mean()
        std25 = close.rolling(window=25).std()
        bb_pos = (close - sma25) / (std25 * 2) * 100
        gap = (open_p / close.shift(1) - 1) * 100
        
        return {
            "price": float(close.iloc[-1]), "dev": float(dev.iloc[-1]), "rsi": float(rsi.iloc[-1]),
            "vol": float(vol_ratio.iloc[-1]), "volatility": float(volatility.iloc[-1]),
            "trend": float(trend_sma.iloc[-1]), "macd": float(macd.iloc[-1]),
            "bb_pos": float(bb_pos.iloc[-1]), "gap": float(gap.iloc[-1])
        }
    except: return None

def run_deep_test():
    xgb_model = joblib.load("xgb_model.pkl")
    lgbm_model = joblib.load("lgbm_model.pkl")
    
    # 全ウォッチリストを対象
    tickers = config.WATCH_LIST[:150]
    total_logs = []

    for ticker in tickers:
        try:
            data = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)
            if data.empty: continue
            
            for i in range(50, len(data) - 6):
                m = calculate_metrics_for_test(data, i)
                if not m: continue
                
                # フィルター緩和 (乖離率 3% 以上のチャンスをすべて拾う)
                if not (3.0 <= m['dev'] <= 25.0): continue
                
                f_input = pd.DataFrame([{
                    'feat_price': m['price'], 'feat_dev': m['dev'], 'feat_rsi': m['rsi'],
                    'feat_vol': m['vol'], 'feat_volatility': m['volatility'], 
                    'feat_trend': m['trend'], 'feat_dayofweek': data.index[i].weekday(),
                    'feat_macd': m['macd'], 'feat_bb_pos': m['bb_pos'], 'feat_gap': m['gap'],
                    'feat_nikkei_trend': 2.0, 'feat_fear_index': 20.0, 'feat_market_phase': 1.0 
                }])
                
                p_xgb = xgb_model.predict_proba(f_input)[0][1]
                p_lgbm = lgbm_model.predict_proba(f_input)[0][1]
                avg_p = (p_xgb + p_lgbm) / 2
                
                if avg_p >= 0.60: # 60%以上の全ての試行を追跡
                    e_price = data['Close'].iloc[i]
                    success = -1
                    for d in range(1, 6):
                        if ((data['High'].iloc[i+d] / e_price) - 1) * 100 >= 1.0:
                            success = 1; break
                        if ((data['Low'].iloc[i+d] / e_price) - 1) * 100 <= -2.0:
                            success = 0; break
                    total_logs.append({"prob": avg_p, "win": success})
        except: continue

    df = pd.DataFrame(total_logs)
    if df.empty:
        print("🕯️ 期間中に該当するチャンスがありませんでした。")
        return

    print("\n🏆 【AI確信度別：1.0% 的中率マトリックス】")
    for th in [0.60, 0.65, 0.70, 0.75, 0.80]:
        t = df[(df['prob'] >= th) & (df['win'] != -1)]
        if not t.empty:
            wr = t['win'].mean() * 100
            print(f"📊 AI判定 {int(th*100)}%以上 ➔ サンプル:{len(t)}回 / 的中率: {wr:.1f}%")

if __name__ == "__main__":
    run_deep_test()
