import pandas as pd
import numpy as np
import yfinance as yf
import joblib
from datetime import datetime, timedelta
from backtest_v19 import NeuralPredator
from core import TICKER_LIST

# --- V20.1: Robustness Test (Out-of-Sample) ---
# 役割: 学習期間外(30日前〜60日前)のデータで V20.0 を検証。
# 相場環境が変わってもエッジが残るかを確認する。

def run_robustness_test():
    print(f"[*] Starting Robustness Test (Out-of-Sample: 60d to 30d ago)...")
    
    # 30日前から60日前までの5分足を取得
    end_date = datetime.now() - timedelta(days=30)
    start_date = datetime.now() - timedelta(days=59)
    
    data = yf.download(TICKER_LIST, 
                       start=start_date.strftime('%Y-%m-%d'), 
                       end=end_date.strftime('%Y-%m-%d'), 
                       interval="5m", 
                       group_by='ticker', 
                       progress=False)
    
    if data.empty:
        print("[ERROR] No data found for this period.")
        return

    # Backtesterを初期化し、データを注入して実行
    tester = NeuralPredator(TICKER_LIST)
    
    # run_backtest をデータ注入型にオーバーライド
    print(f"[*] Simulating {len(data.index)} time steps in UNKNOWN market...")
    
    tester.trade_history = []
    tester.positions = []
    
    timestamps = data.index
    for i in range(50, len(timestamps)):
        tester._update_and_check_exits(data, i, timestamps[i])
        tester._check_entries(data, i, timestamps[i])

    # 結果分析
    if not tester.trade_history:
        print("No trades executed in this period.")
        return
        
    df = pd.DataFrame(tester.trade_history)
    df['win'] = df['pnl'] > 0
    pf = df[df['win']]['pnl'].sum() / (abs(df[~df['win']]['pnl'].sum()) + 1e-9)
    
    print("\n" + "="*40)
    print("V20.1 ROBUSTNESS REPORT (OUT-OF-SAMPLE)")
    print("="*40)
    print(f"Total Trades: {len(df)}")
    print(f"Win Rate: {len(df[df['win']])/len(df)*100:.2f}%")
    print(f"Profit Factor: {pf:.4f}")
    print(f"Total Return: {df['pnl'].sum()*100:.2f}%")
    print("="*40)

if __name__ == "__main__":
    run_robustness_test()
