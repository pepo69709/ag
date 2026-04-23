import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import io

# --- 🚀 利益最大化検証: スイング (+5%) vs マイクロスキャル (+0.5%) ---

TICKERS = ["7733.T", "7203.T", "9984.T", "6758.T", "8035.T", "6501.T", "4063.T"]

START_DATE = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
END_DATE = datetime.now().strftime('%Y-%m-%d')

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def run_backtest(ticker, target_profit, stop_loss, exit_rsi, max_hold_days):
    try:
        df = yf.download(ticker, start=START_DATE, interval="1d", progress=False)
        if df.empty or len(df) < 30: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df['RSI'] = calculate_rsi(df['Close'])
        trades = []
        position = False
        entry_price = 0
        entry_date = None

        for i in range(20, len(df)):
            curr_price = df['Close'].iloc[i]
            rsi = df['RSI'].iloc[i]
            
            if not position and rsi < 30:
                position = True
                entry_price = curr_price
                entry_date = df.index[i]
            elif position:
                profit_pct = (curr_price / entry_price) - 1
                hold_days = (df.index[i] - entry_date).days
                
                # エグジット判定
                if profit_pct >= target_profit or profit_pct <= -stop_loss or rsi > exit_rsi or hold_days > max_hold_days:
                    trades.append(profit_pct * 100)
                    position = False
        return trades
    except: return None

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # A: 現在のスイング (+5% 目標)
    # B: マイクロスキャル (+0.5% 目標)
    
    results_a = []
    results_b = []
    
    print(f"Comparing strategies for {len(TICKERS)} tickers...")
    for t in TICKERS:
        a = run_backtest(t, 0.05, 0.05, 60, 10) # Target 5%, Stop 5%
        b = run_backtest(t, 0.005, 0.005, 40, 3) # Target 0.5%, Stop 0.5%
        if a: results_a.extend(a)
        if b: results_b.extend(b)
    
    def get_stats(trades):
        if not trades: return {"Count": 0, "WinRate": 0, "Sum": 0, "Avg": 0}
        trades = np.array(trades)
        return {
            "Count": len(trades),
            "WinRate": (trades > 0).mean() * 100,
            "Sum": trades.sum(),
            "Avg": trades.mean()
        }

    stats_a = get_stats(results_a)
    stats_b = get_stats(results_b)

    print("\n" + "="*50)
    print("STRATEGY COMPARISON: SWING vs MICRO-SCALP")
    print("="*50)
    print(f"{'Metric':<15} | {'Swing (+5%)':<15} | {'Micro (+0.5%)'}")
    print("-" * 50)
    print(f"{'Trades':<15} | {stats_a['Count']:<15} | {stats_b['Count']}")
    print(f"{'Win Rate %':<15} | {stats_a['WinRate']:<15.2f} | {stats_b['WinRate']:.2f}")
    print(f"{'Sum Profit %':<15} | {stats_a['Sum']:<15.2f} | {stats_b['Sum']:.2f}")
    print(f"{'Avg Profit %':<15} | {stats_a['Avg']:<15.2f} | {stats_b['Avg']:.2f}")
    print("="*50)

if __name__ == "__main__":
    main()
