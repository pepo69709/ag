import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import io

# --- 🚀 極限勝率検証：80%オーバーは可能なのか？ ---
# 「すべての条件が揃った時だけ撃つ」超絶慎重スナイパーの成績を算出

TICKERS = [
    "7203.T", "6758.T", "9984.T", "8035.T", "4063.T", "6501.T", "7733.T", "6954.T", "7267.T", "8001.T",
    "8306.T", "8316.T", "9432.T", "9433.T", "6098.T", "4502.T", "4519.T", "4568.T", "6723.T", "6902.T",
    "6981.T", "7741.T", "7974.T", "8031.T", "8058.T", "8766.T", "8801.T", "8802.T", "9101.T", "9983.T"
]

START_DATE = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')

def run_compare(ticker):
    try:
        df = yf.download(ticker, start=START_DATE, interval="1d", progress=False)
        if df.empty or len(df) < 60: return []
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 指標計算
        delta = df['Close'].diff()
        df['RSI'] = 100 - (100 / (1 + (delta.where(delta > 0, 0).rolling(14).mean() / (-delta.where(delta < 0, 0).rolling(14).mean()))))
        df['MA25'] = df['Close'].rolling(25).mean()
        df['Slope'] = df['MA25'].diff(5)
        df['Vol_Avg'] = df['Volume'].rolling(5).mean()
        
        results = []
        for i in range(30, len(df)):
            curr_p = df['Close'].iloc[i]
            rsi = df['RSI'].iloc[i]
            slope = df['Slope'].iloc[i]
            vol = df['Volume'].iloc[i]
            vol_avg = df['Vol_Avg'].iloc[i]
            
            # --- 判定 ---
            # 普通: RSI < 30
            # 超慎重: RSI < 25 + 出来高1.5倍 + 傾きが水平以上(Slope > -0.1%)
            
            # 純粋RSI
            if rsi < 30:
                results.append({"type": "Normal", "date": df.index[i], "price": curr_p})
            
            # 超慎重 (Ultra Conservative)
            if rsi < 25 and vol > vol_avg * 1.5 and slope > -curr_p * 0.002:
                results.append({"type": "Ultra", "date": df.index[i], "price": curr_p})

        # トレード結果のシミュレーション (簡易版: 5日後の終値で判定)
        sim_trades = []
        for r in results:
            future_idx = df.index.get_indexer([r['date'] + timedelta(days=5)], method='nearest')[0]
            if future_idx < len(df):
                exit_p = df['Close'].iloc[future_idx]
                sim_trades.append({"type": r['type'], "profit": (exit_p / r['price'] - 1) * 100})
        
        return sim_trades
    except: return []

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    all_data = []
    print(f"Testing Ultra-Conservative Win Rate on {len(TICKERS)} tickers...")
    for t in TICKERS:
        res = run_compare(t)
        if res: all_data.extend(res)
    
    df = pd.DataFrame(all_data)
    if df.empty: return
    
    summary = df.groupby('type')['profit'].agg(['count', 'mean', lambda x: (x > 0).mean() * 100]).reset_index()
    summary.columns = ['Strategy', 'Trades', 'Avg Profit%', 'Win Rate%']
    
    print("\n" + "="*60)
    print("WIN RATE vs FREQUENCY: THE ULTIMATE TRADE-OFF")
    print("="*60)
    print(summary.to_string(index=False))
    print("="*60)

if __name__ == "__main__":
    main()
