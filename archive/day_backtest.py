import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import io

# --- ⚙️ デイトレ・バックテスト設定 (楽天証券 0%版) ---
TICKERS = ["7733.T", "7203.T", "9984.T", "6758.T", "8035.T"]
START_DATE = (datetime.now() - timedelta(days=59)).strftime('%Y-%m-%d')
END_DATE = datetime.now().strftime('%Y-%m-%d')

TARGET_PROFIT = 0.010  # +1.0%
STOP_LOSS = 0.005      # -0.5%
FEE = 0.000           # 楽天証券 0円

def run_backtest(ticker):
    print(f"Analyzing {ticker} (Day Trading)...")
    df = yf.download(ticker, start=START_DATE, interval="5m")
    if df.empty: return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df['DateOnly'] = df.index.date
    days = df['DateOnly'].unique()
    results = []
    
    for day in days:
        day_data = df[df['DateOnly'] == day]
        if day_data.empty: continue
        
        entry_price = float(day_data['Open'].iloc[0])
        target_price = entry_price * (1 + TARGET_PROFIT)
        stop_price = entry_price * (1 - STOP_LOSS)
        
        exit_type = "HOLD"
        exit_price = float(day_data['Close'].iloc[-1])
        
        for idx, row in day_data.iterrows():
            high_val = float(row['High'])
            low_val = float(row['Low'])
            if high_val >= target_price:
                exit_type = "GOLD (PROFIT)"
                exit_price = target_price
                break
            elif low_val <= stop_price:
                exit_type = "PURPLE (STOP)"
                exit_price = stop_price
                break
                
        profit_pct = (exit_price / entry_price) - 1
        results.append({"date": day, "profit": profit_pct * 100})
        
    return pd.DataFrame(results)

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    all_res = []
    for t in TICKERS:
        res = run_backtest(t)
        if res is not None: all_res.append(res)
    
    final_df = pd.concat(all_res)
    print("\n" + "="*40)
    print("DAY TRADING RESULT (Last 60 Days / Fee 0%)")
    print("="*40)
    print(f"Total Trades: {len(final_df)}")
    print(f"Avg Profit per Trade: {final_df['profit'].mean():.4f}%")
    print(f"Cumulative Return: {final_df['profit'].sum():.2f}%")
    print("="*40)

if __name__ == "__main__":
    main()
