import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import io

# --- 🚀 出口戦略の究極比較：2%はどうやって利確するのが正解か？ ---
# A: 固定2% (利確指値)
# B: RSI回復 (RSI > 50) ➔ 売られすぎからのフラットな戻り
# C: 移動平均線への回帰 (Price > MA25) ➔ 本格的な平均回帰

TICKERS = [
    "7203.T", "6758.T", "9984.T", "8035.T", "4063.T", "6501.T", "7733.T", "6954.T", "7267.T", "8001.T"
] 

START_DATE = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

def calculate_rsi(data):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    return 100 - (100 / (1 + (gain / loss)))

def backtest_exit(ticker, exit_type):
    try:
        df = yf.download(ticker, start=START_DATE, interval="1d", progress=False)
        if df.empty or len(df) < 50: return []
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df['RSI'] = calculate_rsi(df['Close'])
        df['MA25'] = df['Close'].rolling(25).mean()
        df['Slope'] = df['MA25'].diff(5)
        
        trades = []
        pos = None
        
        for i in range(25, len(df)):
            curr = df['Close'].iloc[i]
            rsi = df['RSI'].iloc[i]
            ma25 = df['MA25'].iloc[i]
            
            if pos is None:
                # エントリー条件 (RSI < 30 + 傾き)
                if rsi < 30 and df['Slope'].iloc[i] > -curr * 0.005:
                    pos = {"price": curr, "date": df.index[i]}
            else:
                p_diff = (curr / pos['price']) - 1
                days = (df.index[i] - pos['date']).days
                
                # エグジット判定
                hit = False
                if exit_type == "FIXED_2PCT" and p_diff >= 0.02: hit = True
                elif exit_type == "RSI_50" and rsi >= 50: hit = True
                elif exit_type == "MA25_TOUCH" and curr >= ma25: hit = True
                
                # 共通損切り
                if p_diff <= -0.03 or days > 15: hit = True
                
                if hit:
                    trades.append({"profit": p_diff * 100, "days": days})
                    pos = None
        return trades
    except: return []

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    results = []
    types = ["FIXED_2PCT", "RSI_50", "MA25_TOUCH"]

    print("Analyzing Exit Indicators (FIXED vs RSI vs MA)...")
    for etype in types:
        all_tr = []
        for t in TICKERS:
            all_tr.extend(backtest_exit(t, etype))
        
        df = pd.DataFrame(all_tr)
        if not df.empty:
            results.append({
                "Exit Logic": etype,
                "Trades": len(df),
                "Win Rate": (df['profit'] > 0).mean() * 100,
                "Avg Profit%": df['profit'].mean(),
                "Avg Days": df['days'].mean()
            })

    summary = pd.DataFrame(results)
    print("\n" + "="*75)
    print("EXIT INDICATOR SHOWDOWN")
    print("="*75)
    print(summary.to_string(index=False))
    print("="*75)

if __name__ == "__main__":
    main()
