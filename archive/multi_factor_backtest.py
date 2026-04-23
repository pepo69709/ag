import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import io

# --- 🚀 マルチ・ファクター検証: RSI + Volume + EMA (500銘柄) ---

TICKERS_BASE = [
    "1332.T", "1605.T", "1801.T", "1925.T", "2502.T", "2914.T", "3382.T", "3402.T", "4063.T", "4452.T",
    "4502.T", "4503.T", "4519.T", "4568.T", "4901.T", "4911.T", "5019.T", "5108.T", "5401.T", "6301.T",
    "6501.T", "6503.T", "6702.T", "6723.T", "6752.T", "6758.T", "6857.T", "6902.T", "6954.T", "6981.T",
    "7011.T", "7203.T", "7267.T", "7733.T", "7741.T", "7974.T", "8001.T", "8031.T", "8035.T", "8058.T",
    "8306.T", "8316.T", "8411.T", "8766.T", "8801.T", "8802.T", "9020.T", "9101.T", "9432.T", "9983.T", "9984.T"
] # 代表的な銘柄で高速に検証

START_DATE = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
END_DATE = datetime.now().strftime('%Y-%m-%d')

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def backtest_multi_factor(ticker):
    try:
        df = yf.download(ticker, start=START_DATE, interval="1d", progress=False)
        if df.empty or len(df) < 30: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 指標計算
        df['RSI'] = calculate_rsi(df['Close'])
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['Vol_Avg'] = df['Volume'].rolling(window=5).mean()
        
        trades = []
        position = False
        entry_price = 0
        entry_date = None

        for i in range(20, len(df)):
            curr_price = df['Close'].iloc[i]
            rsi = df['RSI'].iloc[i]
            vol = df['Volume'].iloc[i]
            vol_avg = df['Vol_Avg'].iloc[i]
            ema20 = df['EMA20'].iloc[i]

            # ランク付けロジック
            score = 1 # 基本(RSI<30)
            if vol > vol_avg * 1.5: score += 1      # Volume Spike
            if curr_price > ema20: score += 1       # Trend Support
            # (他にも乖離率などを追加可能)

            if not position and rsi < 30:
                position = True
                entry_price = curr_price
                entry_date = df.index[i]
                start_score = score
            elif position:
                profit_pct = (curr_price / entry_price) - 1
                hold_days = (df.index[i] - entry_date).days
                if profit_pct >= 0.05 or rsi > 60 or hold_days > 10:
                    trades.append({
                        "score": start_score,
                        "profit": profit_pct * 100
                    })
                    position = False
        return trades
    except: return None

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    results = []
    print(f"Analyzing {len(TICKERS_BASE)} tickers for Multi-Factor Edge...")
    for t in TICKERS_BASE:
        res = backtest_multi_factor(t)
        if res: results.extend(res)
    
    df = pd.DataFrame(results)
    if df.empty: return

    # スコア（星の数）別の成績集計
    report = df.groupby('score')['profit'].agg(['count', 'mean', lambda x: (x > 0).mean() * 100]).reset_index()
    report.columns = ['Stars', 'Trades', 'Avg Profit%', 'Win Rate%']

    print("\n" + "="*50)
    print("MULTI-FACTOR BACKTEST: STAR RANKING PERFORMANCE")
    print("="*50)
    print(report.to_string(index=False))
    print("="*50)
    print("INSIGHT: 星の数が多いほど、勝率や平均利益が向上しているかを確認なのだ！")

if __name__ == "__main__":
    main()
