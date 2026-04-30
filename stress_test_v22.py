import pandas as pd
import numpy as np
import yfinance as yf
import joblib
from datetime import datetime, timedelta
from backtest_v19 import StablePredator
from core import TICKER_LIST

# --- V22.2 Robustness Stress Test ---
# 役割: 魔の期間(60d-30d ago)で V22.2 が生き残れるか検証。
# ここで崩れるなら、V22.2 も「過学習の罠」の中にある。

def run_stress_test():
    print(f"[*] Starting V22.2 Stress Test (Out-of-Sample: 60d to 30d ago)...")
    
    # データを取得
    end_date = datetime.now() - timedelta(days=30)
    start_date = datetime.now() - timedelta(days=59)
    data = yf.download(TICKER_LIST, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), interval="5m", group_by='ticker', progress=False)
    
    if data.empty: return

    # V22.2 ロジックのテスター
    tester = StablePredator(TICKER_LIST)
    tester.trade_history = []
    tester.positions = []
    
    all_dates = data.index.normalize().unique()
    for date in all_dates:
        day_data = data[data.index.normalize() == date]
        if len(day_data) < 50: continue
        
        # 多層判定
        today_morning_score = tester._get_morning_regime_score(day_data)
        combined_regime = (today_morning_score * 0.7) + (tester.prev_day_regime * 0.3)
        
        regime_level = "BAD"
        if combined_regime > 0.6: regime_level = "GOOD"
        elif combined_regime > 0.4: regime_level = "NEUTRAL"
        
        tester.prev_day_regime = combined_regime
        if regime_level == "BAD": continue
        
        timestamps = day_data.index
        for i in range(50, len(timestamps)): # バグ修正後の50スライス
            tester._update_and_check_exits(day_data, i, timestamps[i])
            tester._check_entries(day_data, i, timestamps[i], regime_level)

    # 結果分析
    if not tester.trade_history:
        print("No trades executed in Stress Test.")
        return
        
    df = pd.DataFrame(tester.trade_history)
    pf = df[df['pnl']>0]['pnl'].sum() / (abs(df[df['pnl']<=0]['pnl'].sum()) + 1e-9)
    
    print("\n" + "="*40)
    print("V22.2 STRESS TEST REPORT (60d-30d)")
    print("="*40)
    print(f"Total Trades: {len(df)}")
    print(f"Win Rate: {(df['pnl']>0).mean()*100:.2f}%")
    print(f"Profit Factor: {pf:.4f}")
    print(f"Net Return: {df['pnl'].sum()*100:.2f}%")
    print("="*40)

if __name__ == "__main__":
    run_stress_test()
