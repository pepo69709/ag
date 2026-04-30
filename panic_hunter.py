import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V28.0: The Panic Hunter ---
# 役割: 統計フィルタを捨て、「市場のパニック」という構造的エッジを狙い撃つ。
# 原理: ボラティリティ、出来高、移動平均乖離の同時スパイクによる「弾性反発」の捕捉。

class PanicHunter:
    def __init__(self, tickers):
        self.tickers = tickers
        self.trade_history = []
        self.cost_ratio = 0.0015 # 実戦的な高めコスト設定(0.15%)

    def run_backtest(self, days=60):
        print(f"[*] Scouting for Structural Panic over {days} days...")
        interval = "5m"
        data = yf.download(self.tickers, period=f"{days}d", interval=interval, group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        all_dates = data.index.normalize().unique()
        for date in all_dates:
            day_data = data[data.index.normalize() == date]
            if len(day_data) < 50: continue
            
            for ticker in self.tickers:
                df = day_data[ticker]
                # --- 構造的パニックの検知ロジック ---
                # 1. ボラティリティ・スパイク (Z-Score)
                rets = df['Close'].pct_change()
                vol_std = rets.rolling(20).std()
                vol_z = (rets.abs() - vol_std.rolling(20).mean()) / (vol_std.rolling(20).std() + 1e-9)
                
                # 2. 出来高サージ (平均の5倍以上)
                vol_avg = df['Volume'].rolling(20).mean()
                vol_ratio = df['Volume'] / (vol_avg + 1e-9)
                
                # 3. 価格ストレッチ (20EMAからの乖離)
                ema_20 = df['Close'].ewm(span=20).mean()
                stretch = (df['Close'] - ema_20) / ema_20
                
                for i in range(20, len(df)-5):
                    # パニック条件: ボラ急増 + 出来高急増 + 大幅な下方乖離
                    if vol_z.iloc[i] > 3.0 and vol_ratio.iloc[i] > 5.0 and stretch.iloc[i] < -0.015:
                        entry_price = df['Close'].iloc[i]
                        # 決済シミュレーション: 激しい反発を狙うため、5足以内または反転で利確
                        exit_price = df['Close'].iloc[i+1:i+6].max()
                        pnl = (exit_price / entry_price) - 1
                        
                        # コスト（高め）を差し引く
                        self.trade_history.append({"pnl": pnl - self.cost_ratio, "ticker": ticker})
                        # 重複エントリーを避けるためスキップ
                        i += 10

        self._analyze_results()

    def _analyze_results(self):
        if not self.trade_history: return
        df = pd.DataFrame(self.trade_history)
        pf = df[df['pnl']>0]['pnl'].sum() / (abs(df[df['pnl']<=0]['pnl'].sum()) + 1e-9)
        print(f"\n--- Sniper AI V28.0 Panic Hunter (Structural Edge) ---")
        print(f"Total Trades: {len(df)} | Win Rate: {(df['pnl']>0).mean()*100:.2f}% | PF: {pf:.4f}")
        print(f"Avg Profit per Trade: {df['pnl'].mean()*100:.4f}%")

if __name__ == "__main__":
    from core import TICKER_LIST
    tester = PanicHunter(TICKER_LIST)
    tester.run_backtest(days=60)
