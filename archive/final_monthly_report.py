import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import io

# --- 🚀 最終シミュレーション：12ヶ月間の収支と取引回数の実録 ---
# ・1取引 5,000円
# ・多重買い（シグナルが出たものはすべて買う）
# ・戦略：エリート（RSI < 30 + MA傾きフィルタ）

# 代表的な50銘柄（TOPIX 500等の縮小版）
TICKERS = [
    "7203.T", "6758.T", "9984.T", "8035.T", "4063.T", "6501.T", "7733.T", "6954.T", "7267.T", "8001.T",
    "8306.T", "8316.T", "9432.T", "9433.T", "6098.T", "4502.T", "4519.T", "4568.T", "6723.T", "6902.T",
    "6981.T", "7741.T", "7974.T", "8031.T", "8058.T", "8766.T", "8801.T", "8802.T", "9101.T", "9983.T",
    "1332.T", "1605.T", "1801.T", "1925.T", "2502.T", "2914.T", "3382.T", "3402.T", "4452.T", "4503.T",
    "4901.T", "4911.T", "5019.T", "5108.T", "5401.T", "6301.T", "6503.T", "6702.T", "6752.T", "6857.T"
]

START_DATE = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
INVESTMENT = 5000

def get_rsi(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    return 100 - (100 / (1 + (gain / loss)))

def run_backtest():
    all_trades = []
    print(f"Analyzing {len(TICKERS)} tickers for a 12-month breakdown...")
    
    for t in TICKERS:
        try:
            df = yf.download(t, start=START_DATE, interval="1d", progress=False)
            if df.empty or len(df) < 50: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['RSI'] = get_rsi(df)
            df['MA25'] = df['Close'].rolling(25).mean()
            df['Slope'] = df['MA25'].diff(5)
            
            pos = None
            for i in range(25, len(df)):
                curr = df['Close'].iloc[i]
                if pos is None:
                    # エントリー
                    if df['RSI'].iloc[i] < 30 and df['Slope'].iloc[i] > -curr * 0.005:
                        pos = {"price": curr, "date": df.index[i]}
                else:
                    diff = (curr / pos['price']) - 1
                    days = (df.index[i] - pos['date']).days
                    # 利確 5% / 損切 3% / タイムアウト 15日
                    if diff >= 0.05 or diff <= -0.03 or days > 15:
                        all_trades.append({
                            "month": pos['date'].strftime('%Y-%m'),
                            "profit": INVESTMENT * diff
                        })
                        pos = None
        except: continue
    
    return pd.DataFrame(all_trades)

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    df = run_backtest()
    if df.empty: return

    # 420銘柄換算（倍率: 420 / 50 = 8.4倍）
    SCALE_FACTOR = 420 / len(TICKERS)

    summary = df.groupby('month').agg(
        Trades=('profit', 'count'),
        Profit_Sample=('profit', 'sum')
    )
    
    summary['Estimated_Trades'] = (summary['Trades'] * SCALE_FACTOR).round().astype(int)
    summary['Estimated_Profit'] = (summary['Profit_Sample'] * SCALE_FACTOR).round().astype(int)

    print("\n" + "="*80)
    print("💎 FINAL MONTHLY BREAKDOWN: ELITE SNIPER (5,000 JPY / UNLIMITED SLOTS)")
    print("="*80)
    print(f"Configuration: 420 Tickers Monitor | Target %: +5.0% | Stop %: -3.0%")
    print("-" * 80)
    print(f"{'Month':<10} | {'Trades/Mo':<12} | {'Estimated Profit (JPY)':<25}")
    print("-" * 80)
    
    total_profit = 0
    total_trades = 0
    
    for month, row in summary.iterrows():
        print(f"{month:<10} | {row['Estimated_Trades']:<12} | ¥ {row['Estimated_Profit']:>15,}")
        total_profit += row['Estimated_Profit']
        total_trades += row['Estimated_Trades']
        
    print("-" * 80)
    print(f"{'AVERAGE':<10} | {round(total_trades/len(summary)):<12} | ¥ {round(total_profit/len(summary)):>15,}")
    print("="*80)
    print(f"TOTAL YEARLY PROFIT: ¥ {total_profit:,.0f} (元手5,000円からスタートした場合の威力)")

if __name__ == "__main__":
    main()
