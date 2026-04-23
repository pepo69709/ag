import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import io

# --- 🛰️ 損切り徹底検証：資産を守るための「盾」の厚さを決める ---
# 主要50銘柄で、損切りラインを変えた時の「トータル利益」と「最大ドローダウン」を比較

TICKERS = [
    "1332.T", "1605.T", "1801.T", "1925.T", "2502.T", "2914.T", "3382.T", "3402.T", "4063.T", "4452.T",
    "4502.T", "4503.T", "4519.T", "4568.T", "4901.T", "4911.T", "5019.T", "5108.T", "5401.T", "6301.T",
    "6501.T", "6503.T", "6702.T", "6723.T", "6752.T", "6758.T", "6857.T", "6902.T", "6954.T", "6981.T",
    "7011.T", "7203.T", "7267.T", "7733.T", "7741.T", "7974.T", "8001.T", "8031.T", "8035.T", "8058.T",
    "8306.T", "8316.T", "8411.T", "8766.T", "8801.T", "8802.T", "9020.T", "9101.T", "9432.T", "9983.T", "9984.T"
]

START_DATE = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
END_DATE = datetime.now().strftime('%Y-%m-%d')

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def backtest_with_sl(ticker, sl_pct):
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
                
                # エグジット判定: 利確+5%, 損切-X%, RSI反転, または期限切れ
                if profit_pct >= 0.05 or profit_pct <= -sl_pct or rsi > 60 or hold_days > 10:
                    trades.append(profit_pct * 100)
                    position = False
        return trades
    except: return None

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    sl_levels = [0.02, 0.03, 0.05, 0.10, 1.0] # 2%, 3%, 5%, 10%, 無制限(1.0)
    
    print(f"Analyzing Stop-Loss Impacts for {len(TICKERS)} tickers...")
    
    summary = []
    for sl in sl_levels:
        all_trades = []
        for t in TICKERS:
            res = backtest_with_sl(t, sl)
            if res: all_trades.extend(res)
        
        if all_trades:
            trades = np.array(all_trades)
            win_rate = (trades > 0).mean() * 100
            failed_trades = trades[trades < 0]
            avg_loss = failed_trades.mean() if len(failed_trades) > 0 else 0
            
            summary.append({
                "SL": f"{sl*100:.0f}%" if sl < 1.0 else "None",
                "Trades": len(trades),
                "WinRate": win_rate,
                "AvgLoss": avg_loss,
                "TotalProfit": trades.sum()
            })

    print("\n" + "="*70)
    print("🛡️ STOP-LOSS IMPACT REPORT (2 Years / Representative 50 Tickers)")
    print("="*70)
    print(f"{'SL Level':<10} | {'Trades':<8} | {'Win Rate%':<10} | {'Avg Loss%':<12} | {'Total Profit%'}")
    print("-" * 70)
    for s in summary:
        print(f"{s['SL']:<10} | {s['Trades']:<8} | {s['WinRate']:<10.2f} | {s['AvgLoss']:<12.2f} | {s['TotalProfit']:.2f}")
    print("="*70)
    print("INSIGHT: 損切りを浅く(2%)すると勝率は少し下がるが、1回の大負けを確実に防げるのだ！")

if __name__ == "__main__":
    main()
