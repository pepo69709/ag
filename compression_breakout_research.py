import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V39.0: Compression Breakout Research ---
# 役割: 衝撃後のボラティリティ圧縮(横ばい)から、再拡張(ブレイク)が起きる瞬間を捉える。
# 目的: 方向性のバイアスを捨て、「放たれたエネルギー」に乗る構造的エッジを証明する。

class CompressionBreakout:
    def __init__(self, tickers):
        self.tickers = tickers
        self.results = []

    def run_research(self, days=7):
        print(f"[*] Analyzing Volatility Compression & Expansion after disruption...")
        interval = "1m"
        data = yf.download(self.tickers, period=f"{days}d", interval=interval, group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        all_dates = data.index.normalize().unique()
        for date in all_dates:
            day_data = data[data.index.normalize() == date]
            for ticker in self.tickers:
                df = day_data[ticker]
                if len(df) < 60: continue
                
                # 衝撃検知
                high_low = df['High'] - df['Low']
                tr = pd.concat([high_low, (df['High'] - df['Close'].shift(1)).abs(), (df['Low'] - df['Close'].shift(1)).abs()], axis=1).max(axis=1)
                atr = tr.rolling(20).mean()
                vol_avg = df['Volume'].rolling(20).mean()
                
                for i in range(20, len(df)-20):
                    curr_move = df['Close'].iloc[i] - df['Close'].shift(1).iloc[i]
                    if abs(curr_move) > (atr.iloc[i] * 3.5) and df['Volume'].iloc[i] > (vol_avg.iloc[i] * 10.0) and curr_move < 0:
                        
                        # --- 圧縮区間の特定 (T+1 〜 T+5) ---
                        comp_window = df.iloc[i+1:i+6]
                        range_high = comp_window['High'].max()
                        range_low = comp_window['Low'].min()
                        
                        # ボラ圧縮の強さ (レンジ幅 / 価格)
                        comp_ratio = (range_high - range_low) / df['Close'].iloc[i]
                        
                        # --- 拡張フェーズの観測 (T+6 〜 T+15) ---
                        # ブレイクした方向にエントリーし、10分保持
                        for j in range(i+6, i+16):
                            if j >= len(df): break
                            
                            if df['High'].iloc[j] > range_high: # 上抜け
                                entry_p = range_high * 1.001 # 0.1%滑って買い
                                exit_idx = min(j+10, len(df)-1)
                                pnl = (df['Close'].iloc[exit_idx] / entry_p) - 1
                                self.results.append({"type": "UP_BREAK", "pnl": pnl, "comp": comp_ratio})
                                break
                            
                            if df['Low'].iloc[j] < range_low: # 下抜け
                                entry_p = range_low * 0.999 # 0.1%滑って売り
                                exit_idx = min(j+10, len(df)-1)
                                pnl = (entry_p / df['Close'].iloc[exit_idx]) - 1
                                self.results.append({"type": "DOWN_BREAK", "pnl": pnl, "comp": comp_ratio})
                                break
                        i += 20

        self._analyze_results()

    def _analyze_results(self):
        if not self.results: return
        df = pd.DataFrame(self.results)
        
        print("\n" + "="*70)
        print("COMPRESSION BREAKOUT ANALYSIS (Expansion Alpha)")
        print("="*70)
        
        summary = df.groupby('type').agg({
            'pnl': ['mean', 'count', lambda x: (x > 0).mean()]
        })
        summary.columns = ['Avg_PnL', 'Count', 'WinRate']
        
        print(summary)
        print("-" * 70)
        print(f"Total Alpha Factor: {df['pnl'].mean()*100:+.4f}% (Avg per trade)")
        print("="*70)

if __name__ == "__main__":
    from core import TICKER_LIST
    engine = CompressionBreakout(TICKER_LIST)
    engine.run_research(days=7)
