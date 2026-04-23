import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import io

# --- 🎯 司令官の目標値：月利2万円への挑戦 ---
# 1取引 5000円 で 月2万円 (年24万円) 稼ぐにはどうすればいいか？
# 全35銘柄 (代表サンプル) で全チャンスを拾い切った場合の「理論上の限界利益」を算出

TICKERS = [
    "1332.T", "1605.T", "1801.T", "1925.T", "2502.T", "2914.T", "3382.T", "3402.T", "4063.T", "4452.T",
    "4502.T", "4503.T", "4519.T", "4568.T", "4901.T", "4911.T", "5019.T", "5108.T", "5401.T", "6301.T",
    "6501.T", "6503.T", "6702.T", "6723.T", "6752.T", "6758.T", "6857.T", "6902.T", "6954.T", "6981.T",
    "7011.T", "7203.T", "7267.T", "7733.T", "7741.T"
] 

INVESTMENT_PER_TRADE = 5000
START_DATE = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d') # 直近1年

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def run_limit_test():
    all_trades = []
    print(f"Running Monthly 20,000 JPY Goal Analysis (35 tickers / 1 year)...")
    
    for t in TICKERS:
        try:
            df = yf.download(t, start=START_DATE, interval="1d", progress=False)
            if df.empty or len(df) < 50: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['RSI'] = calculate_rsi(df['Close'])
            df['MA25'] = df['Close'].rolling(25).mean()
            df['Slope'] = df['MA25'].diff(5)
            
            for i in range(25, len(df)):
                curr_p = df['Close'].iloc[i]
                rsi = df['RSI'].iloc[i]
                slope = df['Slope'].iloc[i]
                
                # エリート戦略発動！
                if rsi < 30 and slope > -curr_p * 0.005:
                    # 簡易判定: 10日後のリザルト
                    future_idx = i + 10
                    if future_idx < len(df):
                        p_diff = (df['Close'].iloc[future_idx] / curr_p) - 1
                        all_trades.append({
                            "date": df.index[i],
                            "profit": INVESTMENT_PER_TRADE * p_diff
                        })
        except: continue
    
    return pd.DataFrame(all_trades)

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    results = run_limit_test()
    if results.empty: return

    # 月別利益に集計
    results['month'] = results['date'].dt.to_period('M')
    monthly_profit = results.groupby('month')['profit'].sum()
    
    # 銘柄数が420銘柄になった場合を推定 (420 / 35 = 12倍)
    estimated_monthly = monthly_profit * 12
    
    print("\n" + "="*70)
    print("💰 THE PATH TO 20,000 JPY PER MONTH (ELITE STRATEGY)")
    print("="*70)
    print(f"Sample Tickers: 35 | Target Tickers: 420")
    print("-" * 70)
    print(f"{'Month':<10} | {'Sample Profit':<15} | {'Estimated (420 Tickers)'}")
    print("-" * 70)
    for m, p in monthly_profit.items():
        est = p * 12
        print(f"{str(m):<10} | {p:,.0f} JPY{'':<8} | {est:,.0f} JPY" + (" ✅ GOAL!" if est >= 20000 else ""))
    print("-" * 70)
    print(f"Average Estimated Monthly Profit: {estimated_monthly.mean():,.0f} JPY")
    print("="*70)
    print(f"INSIGHT: 420銘柄あれば、1回5,000円投資でも月平均『約 {estimated_monthly.mean()/1000:,.1f}万円』の利益が狙えるのだ！")

if __name__ == "__main__":
    main()
