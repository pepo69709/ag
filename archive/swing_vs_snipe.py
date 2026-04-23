import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import io

# --- 🚀 戦略比較：スイング (+5%) vs クイック・スナイプ (+2%) ---
# 司令官の「5%は時間がかかる」という直感を検証
# 1取引 5000円 でどちらが「月2万円」に近いか？

TICKERS = [
    "7203.T", "6758.T", "9984.T", "8035.T", "4063.T", "6501.T", "7733.T", "6954.T", "7267.T", "8001.T",
    "8306.T", "8316.T", "9432.T", "9433.T", "6098.T", "4502.T", "4519.T", "4568.T", "6723.T", "6902.T"
] 

INVESTMENT = 5000
START_DATE = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

def calculate_rsi(data):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    return 100 - (100 / (1 + (gain / loss)))

def backtest(ticker, target_pct, stop_pct):
    try:
        df = yf.download(ticker, start=START_DATE, interval="1d", progress=False)
        if df.empty or len(df) < 30: return []
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df['RSI'] = calculate_rsi(df['Close'])
        df['MA25'] = df['Close'].rolling(25).mean()
        df['Slope'] = df['MA25'].diff(5)
        
        trades = []
        pos = None
        
        for i in range(25, len(df)):
            curr = df['Close'].iloc[i]
            if pos is None:
                # エントリー (RSI < 30 + 傾きフィルタ)
                if df['RSI'].iloc[i] < 30 and df['Slope'].iloc[i] > -curr * 0.005:
                    pos = {"price": curr, "date": df.index[i]}
            else:
                diff = (curr / pos['price']) - 1
                days = (df.index[i] - pos['date']).days
                if diff >= target_pct or diff <= -stop_pct or days > 10:
                    trades.append({"profit": INVESTMENT * diff, "days": days})
                    pos = None
        return trades
    except: return []

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    results = []
    configs = [
        {"name": "Swing (+5.0%)", "target": 0.05, "stop": 0.03},
        {"name": "Snipe (+2.0%)", "target": 0.02, "stop": 0.015}
    ]

    print(f"Comparing Strategies on {len(TICKERS)} tickers (1 year)...")
    
    for conf in configs:
        all_tr = []
        for t in TICKERS:
            all_tr.extend(backtest(t, conf['target'], conf['stop']))
        
        df = pd.DataFrame(all_tr)
        if not df.empty:
            results.append({
                "Strategy": conf['name'],
                "Trades": len(df),
                "Win Rate": (df['profit'] > 0).mean() * 100,
                "Avg Days": df['days'].mean(),
                "Total Profit": df['profit'].sum()
            })

    summary = pd.DataFrame(results)
    print("\n" + "="*70)
    print("EXIT STRATEGY COMPARISON: SWING vs SNIPE")
    print("="*70)
    print(summary.to_string(index=False))
    print("="*70)
    print("INSIGHT: 利益を小さく(+2%) すれば、回転率が上がり、資金拘束時間も短くなる。なのだ！🥇")

if __name__ == "__main__":
    main()
