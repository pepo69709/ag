import pandas as pd
import yfinance as yf
import numpy as np
import joblib
import config
import os

print("🔥 【超・ガチ汎化性能テスト：市場連動型 1,500銘柄スキャン】")

def calculate_metrics_for_test(df, i):
    if i < 70: return None
    try:
        d = df.iloc[i-70:i+1]
        close = d['Close'].iloc[:, 0] if len(d['Close'].shape) > 1 else d['Close']
        open_p = d['Open'].iloc[:, 0] if len(d['Open'].shape) > 1 else d['Open']
        vol = d['Volume'].iloc[:, 0] if len(d['Volume'].shape) > 1 else d['Volume']
        
        close = pd.to_numeric(close, errors='coerce').dropna()
        if len(close) < 50: return None
        
        sma25 = close.rolling(window=25).mean()
        sma50 = close.rolling(window=50).mean()
        dev = (close / sma25 - 1) * 100
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss.replace(0, 1e-6)).fillna(0)))
        vol_ratio = vol / vol.rolling(window=20).mean()
        volatility = close.pct_change().rolling(window=10).std() * np.sqrt(252) * 100
        
        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd_hist = (ema12 - ema26) - (ema12 - ema26).ewm(span=9).mean()
        
        bb_pos = (close - sma25) / (close.rolling(window=25).std() * 2) * 100
        gap = (open_p / close.shift(1) - 1) * 100
        
        return {
            "price": float(close.iloc[-1]), "dev": float(dev.iloc[-1]), "rsi": float(rsi.iloc[-1]),
            "vol": float(vol_ratio.iloc[-1]), "volatility": float(volatility.iloc[-1]),
            "trend": float((sma25/sma50).iloc[-1]), "macd": float(macd_hist.iloc[-1]),
            "bb_pos": float(bb_pos.iloc[-1]), "gap": float(gap.iloc[-1]),
            "weekday": d.index[-1].weekday()
        }
    except: return None

def run_real_mega_test():
    xgb_model = joblib.load("xgb_model.pkl")
    lgbm_model = joblib.load("lgbm_model.pkl")
    
    # 日経平均データを取得してマクロ指標を再現
    print("🌍 市場環境データをロード中...")
    nikkei = yf.download("^N225", period="14mo", progress=False, auto_adjust=True)
    n_close = nikkei['Close'].squeeze()
    n_trend_series = (n_close / n_close.shift(20) - 1) * 100
    n_vol_series = n_close.pct_change().rolling(window=20).std() * np.sqrt(252) * 100

    import random
    all_tickers = config.WATCH_LIST
    # 有効そうな銘柄を優先的に100銘柄ピックアップ
    test_tickers = random.sample(all_tickers, min(len(all_tickers), 100))
    
    print(f"📡 {len(test_tickers)}銘柄で検証開始...")
    
    results = []
    for ticker in test_tickers:
        try:
            data = yf.download(ticker, period="1y", progress=False, auto_adjust=True)
            if data.empty: continue
            for i in range(70, len(data) - 6):
                dt = data.index[i]
                if dt not in n_trend_series.index: continue
                
                m = calculate_metrics_for_test(data, i)
                if not m: continue
                
                # 当時の日経データ
                n_t = n_trend_series.loc[dt]
                n_v = n_vol_series.loc[dt]
                n_p = 2 if n_t > 3 else (0 if n_t < -3 else 1)
                
                f_input = pd.DataFrame([{
                    'feat_price': m['price'], 'feat_dev': m['dev'], 'feat_rsi': m['rsi'],
                    'feat_vol': m['vol'], 'feat_volatility': m['volatility'], 
                    'feat_trend': m['trend'], 'feat_dayofweek': m['weekday'],
                    'feat_macd': m['macd'], 'feat_bb_pos': m['bb_pos'], 'feat_gap': m['gap'],
                    'feat_nikkei_trend': n_t, 'feat_fear_index': n_v, 'feat_market_phase': n_p
                }])
                
                avg_p = (xgb_model.predict_proba(f_input)[0][1] + lgbm_model.predict_proba(f_input)[0][1]) / 2
                
                if avg_p >= 0.50:
                    e_p = data['Close'].iloc[i]
                    outcome = 0
                    for d in range(1, 6):
                        if ((data['High'].iloc[i+d] / e_p) - 1) * 100 >= 1.0: outcome = 1; break
                        if ((data['Low'].iloc[i+d] / e_p) - 1) * 100 <= -2.0: break
                    results.append({"prob": avg_p, "win": outcome})
        except: continue

    df = pd.DataFrame(results)
    if df.empty:
        print("🕯️ 依然としてAIが反応しません。1.0%という極小目標に対して、今のモデルが『慎重すぎる』可能性があります。")
        return

    print("\n" + "="*50)
    print("🏆 【真実の汎化性能：確信度別・1%的中率】")
    print("="*50)
    for th in [0.50, 0.60, 0.70, 0.80]:
        t = df[df['prob'] >= th]
        if not t.empty:
            print(f"📊 スコア {int(th*100)}%以上 ➔ 的中率: {t['win'].mean()*100:.1f}% ({len(t)}回判定)")

if __name__ == "__main__":
    run_real_mega_test()
