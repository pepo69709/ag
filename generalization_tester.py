import pandas as pd
import yfinance as yf
import numpy as np
import joblib
import os
from datetime import datetime, timedelta
import config

# ==========================================
# 🛡️ GENERALIZATION TESTER (NO FAKES)
# ==========================================

def calculate_metrics_for_test(df, i):
    """
    scanner.py と全く同じ計算式で、i日目時点の指標を算出
    """
    if i < 50: return None
    try:
        # i日目までのデータを使用
        d = df.iloc[i-50:i+1]
        close = d['Close'].squeeze()
        open_p = d['Open'].squeeze()
        volume = d['Volume'].squeeze()
        
        close = pd.to_numeric(close, errors='coerce').dropna()
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
        macd_hist = (ema12 - ema26) - (ema12 - ema26).ewm(span=9, adjust=False).mean()
        
        std25 = close.rolling(window=25).std()
        bb_pos = (close - sma25) / (std25 * 2) * 100
        
        gap = (open_p / close.shift(1) - 1) * 100
        
        return {
            "price": float(close.iloc[-1]), "dev": float(dev.iloc[-1]), "rsi": float(rsi.iloc[-1]),
            "vol": float(vol_ratio.iloc[-1]), "volatility": float(volatility.iloc[-1]),
            "trend": float(trend_sma.iloc[-1]), "macd": float(macd_hist.iloc[-1]),
            "bb_pos": float(bb_pos.iloc[-1]), "gap": float(gap.iloc[-1])
        }
    except: return None

def run_test():
    print("🚀 汎化性能テスト開始。過去の全データを AI に抜き打ちテストさせます...")
    xgb_model = joblib.load("xgb_model.pkl")
    lgbm_model = joblib.load("lgbm_model.pkl")
    
    tickers = config.WATCH_LIST[:100] # 100銘柄に拡大
    results = []

    for ticker in tickers:
        try:
            data = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)
            if data.empty: continue
            
            for i in range(50, len(data) - 6):
                m = calculate_metrics_for_test(data, i)
                if not m: continue
                
                # スパルタ・フィルター（一次審査）
                if not (config.ENTRY_DEV_MIN <= m['dev'] <= config.ENTRY_DEV_MAX): continue
                
                f_input = pd.DataFrame([{
                    'feat_price': m['price'], 'feat_dev': m['dev'], 'feat_rsi': m['rsi'],
                    'feat_vol': m['vol'], 'feat_volatility': m['volatility'], 
                    'feat_trend': m['trend'], 'feat_dayofweek': data.index[i].weekday(),
                    'feat_macd': m['macd'], 'feat_bb_pos': m['bb_pos'], 'feat_gap': m['gap'],
                    'feat_nikkei_trend': 2.0, 'feat_fear_index': 20.0, 'feat_market_phase': 1.0 # ニュートラルに設定
                }])
                
                p_xgb = xgb_model.predict_proba(f_input)[0][1]
                p_lgbm = lgbm_model.predict_proba(f_input)[0][1]
                avg_p = (p_xgb + p_lgbm) / 2
                
                # 判定（85%基準）
                if avg_p >= 0.85 and p_xgb >= 0.80 and p_lgbm >= 0.80:
                    # 結末確認
                    e_price = data['Close'].iloc[i]
                    outcome = -1 # 未決着
                    for d in range(1, 6):
                        h = data['High'].iloc[i+d]
                        l = data['Low'].iloc[i+d]
                        # +1.0% タッチで勝ち
                        if ((h / e_price) - 1) * 100 >= 1.0:
                            outcome = 1; break
                        # -2.0% タッチで負け
                        if ((l / e_price) - 1) * 100 <= -2.0:
                            outcome = 0; break
                    results.append({"ticker": ticker, "prob": avg_p, "outcome": outcome})
        except: continue

    df = pd.DataFrame(results)
    print("\n" + "="*50)
    print("🏆 【真実の最終レポート：汎化性能検証結果】")
    print("="*50)
    print(f"🎯 検証条件: +1.0% 利確 / -2.0% 損切")
    print(f"📊 遭遇した『黄金シグナル』数: {len(df)}回")
    
    if not df.empty:
        # 結末がついたものだけで集計
        decided = df[df['outcome'] != -1]
        if not decided.empty:
            win_rate = (decided['outcome'].sum() / len(decided)) * 100
            print(f"📈 正解率 (Win Rate): {win_rate:.1f}%")
            print(f"✅ 勝ち: {decided['outcome'].sum()}回")
            print(f"❌ 負け: {len(decided) - decided['outcome'].sum()}回")
            print(f"⏳ 5日間で決着つかず: {len(df) - len(decided)}回")
        else:
            print("⏳ 全てのシグナルが判定継続中（5日以内）です。")
    else:
        print("🕯️ 基準が厳しすぎて、過去データでもシグナルが出ませんでした。")
        print("   ※これは AI が『確信のないところでは沈黙を守った』という誠実さの証でもあります。")

if __name__ == "__main__":
    run_test()
