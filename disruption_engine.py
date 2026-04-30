import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V31.0: Disruption Engine ---
# 役割: Zスコアを廃止し、ATR(物理量)と売買代金(エネルギー)による異常検知を行う。
# 原理: 市場の許容範囲(ATR)を超えた動きと、流動性ショック(Volume Surge)の同期。

class DisruptionEngine:
    def __init__(self, tickers):
        self.tickers = tickers
        self.trade_history = []
        self.cost_ratio = 0.0015 # 実戦的なスリッページ込み

    def run_backtest(self, days=60):
        print(f"[*] Detecting Market Disruption (Non-Stat Logic) over {days} days...")
        interval = "5m"
        data = yf.download(self.tickers, period=f"{days}d", interval=interval, group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        all_dates = data.index.normalize().unique()
        for date in all_dates:
            day_data = data[data.index.normalize() == date]
            for ticker in self.tickers:
                df = day_data[ticker]
                if len(df) < 30: continue
                
                # --- 物理的ディスラプションの検知 ---
                # 1. ATR (真の変動幅)
                high_low = df['High'] - df['Low']
                high_close = (df['High'] - df['Close'].shift(1)).abs()
                low_close = (df['Low'] - df['Close'].shift(1)).abs()
                tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                atr = tr.rolling(20).mean()
                
                # 2. 出来高の絶対的サージ
                vol_avg = df['Volume'].rolling(20).mean()
                
                for i in range(20, len(df)-5):
                    curr_move = df['Close'].iloc[i] - df['Close'].shift(1).iloc[i]
                    # 条件: 1足の動きがATRの3倍超(物理的限界) かつ 出来高が平均の8倍超(流動性崩壊)
                    if abs(curr_move) > (atr.iloc[i] * 3.0) and df['Volume'].iloc[i] > (vol_avg.iloc[i] * 8.0) and curr_move < 0:
                        entry_p = df['Close'].iloc[i]
                        # 激しいリバウンド(Re-equilibrium)を狙う
                        exit_p = df['Close'].iloc[i+1:i+6].max()
                        pnl = (exit_p / entry_p) - 1
                        
                        self.trade_history.append({"pnl": pnl - self.cost_ratio, "ticker": ticker, "move_atr": abs(curr_move)/atr.iloc[i]})
                        i += 5

        self._analyze_results()

    def _analyze_results(self):
        if not self.trade_history: return
        df = pd.DataFrame(self.trade_history)
        pf = df[df['pnl']>0]['pnl'].sum() / (abs(df[df['pnl']<=0]['pnl'].sum()) + 1e-9)
        print(f"\n--- Sniper AI V31.0 Disruption Engine ---")
        print(f"Total Trades: {len(df)} | Win Rate: {(df['pnl']>0).mean()*100:.2f}% | PF: {pf:.4f}")
        print(f"Avg Move (ATR Ratio): {df['move_atr'].mean():.2f}")

if __name__ == "__main__":
    from core import TICKER_LIST
    engine = DisruptionEngine(TICKER_LIST)
    engine.run_backtest(days=60)
