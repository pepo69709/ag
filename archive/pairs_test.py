import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import io

# --- 🚀 機関投資家（ゴールドマン等）の秘奥義：統計的裁定（ペアトレード） ---
# 似た動きをする2銘柄（トヨタとホンダなど）の「ズレ」を利益に変える

SYMBOLS = ["7203.T", "7267.T"] # トヨタ と ホンダ
START_DATE = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')

def run_pairs_trading():
    try:
        # 2銘柄のデータを取得
        data = yf.download(SYMBOLS, start=START_DATE, interval="1d", progress=False)['Close']
        if data.empty: return
        
        # z-score (価格差の標準偏差からの乖離) を計算
        # 1. 価格比（レシオ）
        ratio = data[SYMBOLS[0]] / data[SYMBOLS[1]]
        # 2. 移動平均と標準偏差
        ma = ratio.rolling(window=20).mean()
        std = ratio.rolling(window=20).std()
        z_score = (ratio - ma) / std
        
        trades = []
        position = 0 # 1: Long Ratio, -1: Short Ratio
        
        for i in range(20, len(z_score)):
            z = z_score.iloc[i]
            r = ratio.iloc[i]
            
            # --- ロジック ---
            # z > 2  : 比率が上がりすぎ ➔ トヨタを売り、ホンダを買う
            # z < -2 : 比率が下がりすぎ ➔ トヨタを買い、ホンダを売る
            # z == 0 : 平均に戻った ➔ 決済
            
            if position == 0:
                if z > 2.0:
                    position = -1 # Short the ratio
                    entry_ratio = r
                elif z < -2.0:
                    position = 1 # Long the ratio
                    entry_ratio = r
            elif position == 1 and z >= 0: # 戻った！
                trades.append((r / entry_ratio - 1) * 100)
                position = 0
            elif position == -1 and z <= 0: # 戻った！
                trades.append((entry_ratio / r - 1) * 100)
                position = 0
        
        return trades
    except Exception as e:
        print(f"Error: {e}")
        return []

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print(f"Testing Institutional 'Statistical Arbitrage' on {SYMBOLS}...")
    trades = run_pairs_trading()
    
    if trades:
        res = np.array(trades)
        print("\n" + "="*60)
        print(f"PAIRS TRADING RESULT: {SYMBOLS[0]} vs {SYMBOLS[1]}")
        print("="*60)
        print(f"Total Trades: {len(res)}")
        print(f"Win Rate: {(res > 0).mean() * 100:.2f}%")
        print(f"Sum Profit%: {res.sum():.2f}%")
        print("="*60)
        print("INSIGHT: 市場全体が暴落しても、この2銘柄の『差』が戻れば儲かる。これが機関投資家の『負けない』秘密なのだ！")

if __name__ == "__main__":
    main()
