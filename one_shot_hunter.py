import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import time
from core import TICKER_LIST, SniperCoreV42

def one_shot_hunt():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sniper AI V19.6: Starting Real-time Hunt...")
    
    # 1. エンジン初期化
    core_engine = SniperCoreV42()
    
    # 2. データ取得
    data = yf.download(TICKER_LIST, period="1d", interval="1m", group_by='ticker', progress=False)
    
    results = []
    for ticker in TICKER_LIST:
        try:
            df = data[ticker].iloc[-60:]
            if df.isnull().values.any(): continue
            
            # 指標算出 (core.pyのロジックを使用)
            # predict_v42 は詳細な辞書を返す
            res = core_engine.predict_v42(ticker, df)
            
            # --- V19.1: Predator Guard Filters (Balanced) ---
            vol = res["volatility"]
            pb_ratio = res["pullback"] / (vol + 1e-9)
            
            if pb_ratio < 0.8: continue
            if res["recent_surge"] > (vol * 3.5): continue
            if vol < 0.003: continue
            
            res["ticker"] = ticker
            res["pb_ratio"] = pb_ratio
            results.append(res)
        except Exception as e:
            # print(f"Error skipping {ticker}: {e}")
            continue
    
    if not results:
        print("No candidates passed the guard filters.")
        return

    score_df = pd.DataFrame(results)
    
    # --- V19.7: Unmuted ML Scoring (Additive) ---
    # 確率の崩壊(0.3%問題)を防ぐため、掛け算から足し算へ
    ml_score = (score_df['pred_return'] * 0.7) + (score_df['confidence'] * 0.3)
    
    # --- V19.3: Market Regime Detection ---
    market_avg_ret = ml_score.mean()
    regime_boost = 1.1 if market_avg_ret > 0 else 0.8
    print(f"Market Regime: {'BULL' if market_avg_ret > 0 else 'BEAR'} (Boost: {regime_boost})")

    # --- V19.1/V19.5: Precision Predator Scoring ---
    pb_center, pb_width = 2.5, 1.5
    pullback_score = np.exp(-((score_df['pb_ratio'] - pb_center) ** 2) / (2 * pb_width ** 2))
    cooldown_raw = -score_df['recent_surge'] / (score_df['volatility'] + 1e-6)
    cooldown_score = np.clip(cooldown_raw / 1.5, 0, 1)
    
    score_df['blended_score'] = (
        ml_score * 0.50 + 
        pullback_score * 0.35 + 
        cooldown_score * 0.15
    ) * regime_boost
    
    score_df['final_score'] = (score_df['blended_score'] - score_df['blended_score'].mean()) / (score_df['blended_score'].std() + 1e-6)
    
    # V19.5: Elite Boost & Threshold
    score_df.loc[score_df['final_score'] > 0.9, 'final_score'] *= 1.15
    score_df = score_df[score_df['final_score'] >= 0.72]

    if score_df.empty:
        print("No candidates reached the Sniper Threshold (0.72). Wait for better edge.")
        return

    top_candidates = score_df.sort_values(by="final_score", ascending=False).head(1)
    
    print("\n" + "="*40)
    print("🎯 SNIPER ELITE: TOP CANDIDATE")
    print("="*40)
    for _, row in top_candidates.iterrows():
        print(f"Ticker      : {row['ticker']}")
        print(f"Confidence  : {row['confidence']:.3f}")
        print(f"True EV     : {row['true_ev']:.4f}")
        print(f"PB Ratio    : {row['pb_ratio']:.2f}")
        print(f"Final Score : {row['final_score']:.3f}")
    print("="*40)
    print("\n[V19.6] この銘柄はデータに基づき、現在最も高い期待値を持っています。")

if __name__ == "__main__":
    one_shot_hunt()
