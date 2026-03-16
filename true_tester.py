import pandas as pd
import yfinance as yf
import numpy as np
import joblib
import os
import config

print("🛡️ 【正解率の真実：シン・汎化性能テスター】")

def calculate_metrics_raw(df, i):
    """
    次元エラーを徹底排除した正確な計算ロジック
    """
    if i < 70: return None # 余裕を持たせる
    d = df.iloc[i-70:i+1] # 直近70日
    # MultiIndex対策
    close = d['Close'].iloc[:,0] if len(d['Close'].shape)>1 else d['Close']
    open_p = d['Open'].iloc[:,0] if len(d['Open'].shape)>1 else d['Open']
    vol = d['Volume'].iloc[:,0] if len(d['Volume'].shape)>1 else d['Volume']
    
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
    macd = (close.ewm(span=12).mean() - close.ewm(span=26).mean())
    macd_hist = macd - macd.ewm(span=9).mean()
    bb_pos = (close - sma25) / (close.rolling(window=25).std() * 2) * 100
    gap = (open_p / close.shift(1) - 1) * 100
    
    return {
        "price": float(close.iloc[-1]), "dev": float(dev.iloc[-1]), "rsi": float(rsi.iloc[-1]),
        "vol": float(vol_ratio.iloc[-1]), "volatility": float(volatility.iloc[-1]),
        "trend": float((sma25/sma50).iloc[-1]), "macd": float(macd_hist.iloc[-1]),
        "bb_pos": float(bb_pos.iloc[-1]), "gap": float(gap.iloc[-1]),
        "weekday": d.index[-1].weekday()
    }

def run_true_test():
    xgb_model = joblib.load("xgb_model.pkl")
    lgbm_model = joblib.load("lgbm_model.pkl")
    
    # 低価格帯の「AIの主戦場」から50銘柄抽出
    tickers = ['1332.T', '1802.T', '2337.T', '2503.T', '3101.T', '4005.T', '5406.T', '6752.T', '7201.T', '8306.T', '9501.T'] # 厳選
    results = []

    for ticker in tickers:
        try:
            data = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)
            if data.empty: continue
            for i in range(70, len(data) - 6):
                m = calculate_metrics_raw(data, i)
                if not m or not (2.0 <= m['dev'] <= 25.0): continue
                
                f_input = pd.DataFrame([{
                    'feat_price': m['price'], 'feat_dev': m['dev'], 'feat_rsi': m['rsi'],
                    'feat_vol': m['vol'], 'feat_volatility': m['volatility'], 
                    'feat_trend': m['trend'], 'feat_dayofweek': m['weekday'],
                    'feat_macd': m['macd'], 'feat_bb_pos': m['bb_pos'], 'feat_gap': m['gap'],
                    'feat_nikkei_trend': 2.0, 'feat_fear_index': 20.0, 'feat_market_phase': 1.0
                }])
                
                avg_p = (xgb_model.predict_proba(f_input)[0][1] + lgbm_model.predict_proba(f_input)[0][1]) / 2
                
                if avg_p >= 0.65: # 65% をハードルに設定
                    e_price = data['Close'].iloc[i]
                    win = 0
                    for d in range(1, 6):
                        if ((data['High'].iloc[i+d] / e_price) - 1) * 100 >= 1.0: win = 1; break
                        if ((data['Low'].iloc[i+d] / e_price) - 1) * 100 <= -2.0: break
                    results.append({"prob": avg_p, "win": win})
        except: continue

    df = pd.DataFrame(results)
    if df.empty:
        print("🕯️ 基準に達するシグナルが見つかりませんでした。モデルの学習範囲外のようです。")
        return

    print(f"\n📊 【AI的中率レポート】")
    for row in [0.65, 0.70, 0.75, 0.80]:
        t = df[df['prob'] >= row]
        if not t.empty:
            print(f"🔹 確信度 {int(row*100)}% 以上 ➔ 成功率: {t['win'].mean()*100:.1f}% ({len(t)}件中)")

if __name__ == "__main__":
    run_true_test()
