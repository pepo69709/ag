import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V31.1: Disruption Truth Test ---
# 役割: 未来参照バイアス(Lookahead Bias)を排除し、物理エッジの「真の姿」を暴く。
# 手法: ATR/Volumeトリガーは維持し、出口を「3本後のClose」に完全固定。

class DisruptionTruth:
    def __init__(self, tickers):
        self.tickers = tickers
        self.trade_history = []
        self.cost_ratio = 0.0015 # 実戦的コスト (0.15%)

    def run_truth_test(self, days=60):
        print(f"[*] Executing Truth Test (Fixed Exit) over {days} days...")
        interval = "5m"
        data = yf.download(self.tickers, period=f"{days}d", interval=interval, group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        all_dates = data.index.normalize().unique()
        for date in all_dates:
            # 日付でスライス
            day_data = data[data.index.normalize() == date]
            for ticker in self.tickers:
                df = day_data[ticker]
                if len(df) < 30: continue
                
                # ATR計算
                high_low = df['High'] - df['Low']
                high_close = (df['High'] - df['Close'].shift(1)).abs()
                low_close = (df['Low'] - df['Close'].shift(1)).abs()
                tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                atr = tr.rolling(20).mean()
                vol_avg = df['Volume'].rolling(20).mean()
                
                for i in range(20, len(df)-4):
                    curr_move = df['Close'].iloc[i] - df['Close'].shift(1).iloc[i]
                    
                    # トリガー: 物理的限界(ATR 3倍) + 流動性ショック(Vol 8倍)
                    if abs(curr_move) > (atr.iloc[i] * 3.0) and df['Volume'].iloc[i] > (vol_avg.iloc[i] * 8.0) and curr_move < 0:
                        entry_p = df['Close'].iloc[i]
                        
                        # --- V31.1: 盲目的決済 (3本後の終値で強制決済) ---
                        exit_idx = min(i + 3, len(df)-1)
                        exit_p = df['Close'].iloc[exit_idx]
                        
                        pnl = (exit_p / entry_p) - 1
                        self.trade_history.append({
                            "pnl": pnl - self.cost_ratio, 
                            "ticker": ticker, 
                            "hold_time": (exit_idx - i) * 5
                        })
                        i = exit_idx # 重複回避

        self._analyze_results()

    def _analyze_results(self):
        if not self.trade_history: return
        df = pd.DataFrame(self.trade_history)
        win_sum = df[df['pnl']>0]['pnl'].sum()
        loss_sum = abs(df[df['pnl']<=0]['pnl'].sum())
        pf = win_sum / (loss_sum + 1e-9)
        
        print(f"\n" + "="*40)
        print("DISRUPTION TRUTH TEST REPORT")
        print("="*40)
        print(f"Total Trades: {len(df)}")
        print(f"Win Rate: {(df['pnl']>0).mean()*100:.2f}%")
        print(f"Profit Factor: {pf:.4f}")
        print(f"Avg PnL per Trade: {df['pnl'].mean()*100:+.4f}%")
        print("="*40)

if __name__ == "__main__":
    from core import TICKER_LIST
    engine = DisruptionTruth(TICKER_LIST)
    engine.run_truth_test(days=60)
