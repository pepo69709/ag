import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import io

# --- 🚀 最終証明：エリート・スナイパー戦略 (5000円固定投資) ---
# ロジック: RSI < 30 + MA傾きフィルター (急落排除)
# 出口: 利確 5% / 損切 3% / RSI 60以上回復 / 15日経過

TICKERS = [
    "1332.T", "1605.T", "1801.T", "1925.T", "2502.T", "2914.T", "3382.T", "3402.T", "4063.T", "4452.T",
    "4502.T", "4503.T", "4519.T", "4568.T", "4901.T", "4911.T", "5019.T", "5108.T", "5401.T", "6301.T",
    "6501.T", "6503.T", "6702.T", "6723.T", "6752.T", "6758.T", "6857.T", "6902.T", "6954.T", "6981.T",
    "7011.T", "7203.T", "7267.T", "7733.T", "7741.T", "7974.T", "8001.T", "8031.T", "8035.T", "8058.T",
    "8306.T", "8316.T", "8411.T", "8766.T", "8801.T", "8802.T", "9020.T", "9101.T", "9432.T", "9983.T", "9984.T"
] # 代表51銘柄 (全420銘柄の縮小版として検証)

INVESTMENT_PER_TRADE = 5000
START_DATE = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def backtest_elite(ticker):
    try:
        df = yf.download(ticker, start=START_DATE, interval="1d", progress=False)
        if df.empty or len(df) < 30: return []
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df['RSI'] = calculate_rsi(df['Close'])
        df['MA25'] = df['Close'].rolling(window=25).mean()
        df['Slope'] = df['MA25'].diff(5)
        
        trades = []
        position = False
        entry_price = 0
        entry_date = None

        for i in range(25, len(df)):
            curr_p = df['Close'].iloc[i]
            rsi = df['RSI'].iloc[i]
            slope = df['Slope'].iloc[i]
            
            # --- エントリー条件 ---
            # RSI < 30 かつ 25日線の傾きが穏やか (急落を避ける)
            if not position and rsi < 30 and slope > -curr_p * 0.005: 
                position = True
                entry_price = curr_p
                entry_date = df.index[i]
            elif position:
                p_diff = (curr_p / entry_price) - 1
                days = (df.index[i] - entry_date).days
                # エグジット
                if p_diff >= 0.05 or p_diff <= -0.03 or rsi > 60 or days > 15:
                    profit_yen = INVESTMENT_PER_TRADE * p_diff
                    trades.append({"date": df.index[i], "profit": profit_yen, "p_pct": p_diff * 100})
                    position = False
        return trades
    except: return []

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    all_trades = []
    print(f"Final Elite Validation: 2 years / {len(TICKERS)} tickers / 5000 JPY per trade")
    for t in TICKERS:
        res = backtest_elite(t)
        if res: all_trades.extend(res)
    
    df = pd.DataFrame(all_trades)
    if df.empty:
        print("No trades found.")
        return

    # 集計
    total_profit = df['profit'].sum()
    win_rate = (df['profit'] > 0).mean() * 100
    avg_gain = df[df['profit'] > 0]['p_pct'].mean()
    avg_loss = df[df['profit'] < 0]['p_pct'].mean()
    
    print("\n" + "="*70)
    print("📈 ELITE SNIPER FINAL REPORT (5000 YEN UNIT)")
    print("="*70)
    print(f"Total Trades    : {len(df)}")
    print(f"Win Rate        : {win_rate:.2f}%")
    print(f"Avg Profit %    : +{avg_gain:.2f}%")
    print(f"Avg Loss %      : {avg_loss:.2f}%")
    print(f"Net Profit (Yen): {total_profit:,.0f} JPY")
    print("="*70)
    print(f"INSIGHT: 50銘柄だけで『2年間、1回5000円』を使い回すと約 {total_profit/1000:,.1f}万円 増える計算なのだ！")
    print(f"これを420銘柄に広げれば、単純計算でさらに 8倍、約 {total_profit*8/1000:,.0f}万円 以上の利益が狙えるのだ！")

if __name__ == "__main__":
    main()
