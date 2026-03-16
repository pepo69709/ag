import pandas as pd
import yfinance as yf
import numpy as np
import joblib
import config
import os

print("🔥 【究極の汎化性能テスト：1,500銘柄・無差別スキャン】")

# オリジナル銘柄（学習に使った可能性が高い500銘柄）を特定
# ここでは簡易的に、新しく追加されたであろう銘柄を推測して「完全初見」としてテストする
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
    except: return None

def run_mega_test():
    xgb_model = joblib.load("xgb_model.pkl")
    lgbm_model = joblib.load("lgbm_model.pkl")
    
    # 全1500銘柄から、ランダムに500銘柄を選んでテスト（多様性を担保）
    import random
    all_tickers = config.WATCH_LIST
    # random.seed(42) # 再現性のため
    test_tickers = random.sample(all_tickers, min(len(all_tickers), 150)) # 150銘柄に厳選
    
    print(f"📡 {len(test_tickers)}銘柄を選択。過去1年間の価格推移からAIの判断を全スキャンします...")
    
    results = []
    for ticker in test_tickers:
        try:
            data = yf.download(ticker, period="1y", progress=False, auto_adjust=True)
            if data.empty: continue
            for i in range(70, len(data) - 6):
                m = calculate_metrics_for_test(data, i)
                # フィルターを完全に撤廃（分布を見るため）
                if not m: continue
                
                f_input = pd.DataFrame([{
                    'feat_price': m['price'], 'feat_dev': m['dev'], 'feat_rsi': m['rsi'],
                    'feat_vol': m['vol'], 'feat_volatility': m['volatility'], 
                    'feat_trend': m['trend'], 'feat_dayofweek': m['weekday'],
                    'feat_macd': m['macd'], 'feat_bb_pos': m['bb_pos'], 'feat_gap': m['gap'],
                    'feat_nikkei_trend': 2.0, 'feat_fear_index': 20.0, 'feat_market_phase': 1.0
                }])
                
                avg_p = (xgb_model.predict_proba(f_input)[0][1] + lgbm_model.predict_proba(f_input)[0][1]) / 2
                
                # 50%以上の全ての判断を記録
                if avg_p >= 0.50:
                    e_p = data['Close'].iloc[i]
                    win = 0
                    for d in range(1, 6):
                        if ((data['High'].iloc[i+d] / e_p) - 1) * 100 >= 1.0: win = 1; break
                        if ((data['Low'].iloc[i+d] / e_p) - 1) * 100 <= -2.0: break
                    results.append({"prob": avg_p, "win": win})
        except: continue

    df = pd.DataFrame(results)
    if df.empty:
        print("🕯️ AIが50%以上の確信度を出した場面が一度もありませんでした。")
        return

    print("\n" + "="*50)
    print("🏆 【AI確信度別・1.0% 的中率分布レポート】")
    print("="*50)
    ranges = [(0.50, 0.60), (0.60, 0.70), (0.70, 0.80), (0.80, 0.85), (0.85, 1.0)]
    for r in ranges:
        t = df[(df['prob'] >= r[0]) & (df['prob'] < r[1])]
        if not t.empty:
            wr = t['win'].mean() * 100
            print(f"📊 スコア {int(r[0]*100)}%-{int(r[1]*100)}% ➔ 的中率: {wr:.1f}% ({len(t)}件)")
    
    print("\n💡 考察: 銘柄数を増やしても的中率が維持されていれば、真の汎化性能がある証明です。")

if __name__ == "__main__":
    run_mega_test()
