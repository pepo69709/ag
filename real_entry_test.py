import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V34.0: Real Entry Test ---
# 役割: 39件の全イベントに対し、現実的な「遅延 + コスト」を課してリターン分布を抽出。
# 目的: 特定の成功例に依存しない、戦略全体の期待値とリスクを可視化する。

class RealEntryTest:
    def __init__(self, tickers):
        self.tickers = tickers
        self.results = []

    def run_distribution_test(self, days=7):
        print(f"[*] Extracting Cold Distribution over {days} days (1m resolution)...")
        interval = "1m"
        data = yf.download(self.tickers, period=f"{days}d", interval=interval, group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        all_dates = data.index.normalize().unique()
        for date in all_dates:
            day_data = data[data.index.normalize() == date]
            for ticker in self.tickers:
                df = day_data[ticker]
                if len(df) < 60: continue
                
                # 異常検知 (ATR 3.5倍 / Vol 10倍)
                high_low = df['High'] - df['Low']
                tr = pd.concat([high_low, (df['High'] - df['Close'].shift(1)).abs(), (df['Low'] - df['Close'].shift(1)).abs()], axis=1).max(axis=1)
                atr = tr.rolling(20).mean()
                vol_avg = df['Volume'].rolling(20).mean()
                
                for i in range(20, len(df)-10):
                    curr_move = df['Close'].iloc[i] - df['Close'].shift(1).iloc[i]
                    if abs(curr_move) > (atr.iloc[i] * 3.5) and df['Volume'].iloc[i] > (vol_avg.iloc[i] * 10.0) and curr_move < 0:
                        
                        # --- V34.0: 現実的エントリーシミュレーション ---
                        # 1. 衝撃の次の足の始値で約定
                        # 2. さらに 0.1% のスリッページを課す
                        if i + 1 >= len(df): continue
                        entry_p = df['Open'].iloc[i+1] * 1.001 
                        
                        # エントリー後1-5分のリターン分布
                        ret_1m = (df['Close'].iloc[i+1] / entry_p) - 1
                        ret_2m = (df['Close'].iloc[i+2] / entry_p) - 1 if i+2 < len(df) else ret_1m
                        ret_3m = (df['Close'].iloc[i+3] / entry_p) - 1 if i+3 < len(df) else ret_2m
                        ret_5m = (df['Close'].iloc[i+5] / entry_p) - 1 if i+5 < len(df) else ret_3m
                        
                        # 衝撃の強さとその後を記録
                        self.results.append({
                            "ts": df.index[i], "ticker": ticker,
                            "atr_x": abs(curr_move)/atr.iloc[i],
                            "ret_1m": ret_1m, "ret_2m": ret_2m, "ret_3m": ret_3m, "ret_5m": ret_5m
                        })
                        i += 15 # 重複回避

        self._analyze_distribution()

    def _analyze_distribution(self):
        if not self.results: return
        df = pd.DataFrame(self.results)
        
        print("\n" + "="*60)
        print("REAL ENTRY DISTRIBUTION REPORT")
        print("="*60)
        print(f"Total Events Sampled: {len(df)}")
        
        for m in [1, 2, 3, 5]:
            col = f"ret_{m}m"
            mean_ret = df[col].mean() * 100
            win_rate = (df[col] > 0).mean() * 100
            max_loss = df[col].min() * 100
            print(f"[{m}min Hold] Mean: {mean_ret:+.3f}% | WinRate: {win_rate:.1f}% | Worst: {max_loss:+.2f}%")
        
        print("-" * 60)
        # 成功例と失敗例の代表を出す
        df_sorted = df.sort_values(by="ret_3m", ascending=False)
        print(f"Best:  {df_sorted.iloc[0]['ticker']} at {df_sorted.iloc[0]['ts']} (PnL: {df_sorted.iloc[0]['ret_3m']*100:+.2f}%)")
        print(f"Worst: {df_sorted.iloc[-1]['ticker']} at {df_sorted.iloc[-1]['ts']} (PnL: {df_sorted.iloc[-1]['ret_3m']*100:+.2f}%)")
        print("="*60)

if __name__ == "__main__":
    from core import TICKER_LIST
    tester = RealEntryTest(TICKER_LIST)
    tester.run_distribution_test(days=7)
