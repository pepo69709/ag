import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V40.0: Persistence Research ---
# 役割: ブレイク初動の「ノイズ」を捨て、3分後の「確証されたトレンド」に乗る。
# 目的: エントリーをあえて遅らせることで、コスト耐性と再現性を劇的に向上させる。

class PersistenceHunter:
    def __init__(self, tickers):
        self.tickers = tickers
        self.results = []

    def run_research(self, days=7):
        print(f"[*] Analyzing Post-Breakout Persistence (3m Delay) over {days} days...")
        interval = "1m"
        data = yf.download(self.tickers, period=f"{days}d", interval=interval, group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        all_dates = data.index.normalize().unique()
        for date in all_dates:
            day_data = data[data.index.normalize() == date]
            for ticker in self.tickers:
                df = day_data[ticker]
                if len(df) < 60: continue
                
                # 衝撃 ➡ 圧縮
                high_low = df['High'] - df['Low']
                tr = pd.concat([high_low, (df['High'] - df['Close'].shift(1)).abs(), (df['Low'] - df['Close'].shift(1)).abs()], axis=1).max(axis=1)
                atr = tr.rolling(20).mean()
                vol_avg = df['Volume'].rolling(20).mean()
                
                for i in range(20, len(df)-25):
                    curr_move = df['Close'].iloc[i] - df['Close'].shift(1).iloc[i]
                    if abs(curr_move) > (atr.iloc[i] * 3.5) and df['Volume'].iloc[i] > (vol_avg.iloc[i] * 10.0) and curr_move < 0:
                        
                        # 圧縮区間 (T+1 〜 T+5)
                        comp_window = df.iloc[i+1:i+6]
                        range_high = comp_window['High'].max()
                        range_low = comp_window['Low'].min()
                        
                        # ブレイク観測 (T+6 〜 T+15)
                        for j in range(i+6, i+16):
                            if j + 10 >= len(df): break
                            
                            type = None
                            if df['High'].iloc[j] > range_high: type = "UP"
                            elif df['Low'].iloc[j] < range_low: type = "DOWN"
                            
                            if type:
                                # --- V40.0: 遅延エントリー (3分待つ) ---
                                delay_idx = j + 3
                                if delay_idx >= len(df): break
                                
                                # 3分後もトレンドが継続しているか(Confirmation)
                                confirmed = False
                                if type == "UP" and df['Close'].iloc[delay_idx] > range_high: confirmed = True
                                if type == "DOWN" and df['Close'].iloc[delay_idx] < range_low: confirmed = True
                                
                                if confirmed:
                                    entry_p = df['Close'].iloc[delay_idx]
                                    # さらに10分保持
                                    exit_idx = min(delay_idx + 10, len(df)-1)
                                    pnl = (df['Close'].iloc[exit_idx] / entry_p) - 1 if type == "UP" else (entry_p / df['Close'].iloc[exit_idx]) - 1
                                    
                                    # コスト 0.1% を差し引く
                                    self.results.append({"type": type, "pnl": pnl - 0.001})
                                break
                        i += 25

        self._analyze_results()

    def _analyze_results(self):
        if not self.results: return
        df = pd.DataFrame(self.results)
        
        print("\n" + "="*70)
        print("PERSISTENCE ANALYSIS (3m Delayed Entry)")
        print("="*70)
        
        summary = df.groupby('type').agg({
            'pnl': ['mean', 'count', lambda x: (x > 0).mean()]
        })
        summary.columns = ['Avg_PnL', 'Count', 'WinRate']
        
        print(summary)
        print("-" * 70)
        print(f"Total Alpha: {df['pnl'].mean()*100:+.4f}% (After 0.1% Slip)")
        print("="*70)

if __name__ == "__main__":
    from core import TICKER_LIST
    hunter = PersistenceHunter(TICKER_LIST)
    hunter.run_research(days=7)
