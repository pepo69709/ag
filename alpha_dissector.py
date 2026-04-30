import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V29.0: Alpha Dissector ---
# 役割: 成功した7トレードを解剖し、反発の「物理的理由」を特定する。
# 手法: 詳細なログ出力 + 過酷な条件下での利益残存チェック。

class AlphaDissector:
    def __init__(self, tickers):
        self.tickers = tickers
        self.logs = []

    def dissect_panic(self, days=60):
        print(f"[*] Dissecting Alpha in {days} days of data...")
        interval = "5m"
        data = yf.download(self.tickers, period=f"{days}d", interval=interval, group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        all_dates = data.index.normalize().unique()
        for date in all_dates:
            day_data = data[data.index.normalize() == date]
            for ticker in self.tickers:
                df = day_data[ticker]
                # 指標計算
                rets = df['Close'].pct_change()
                vol_std = rets.rolling(20).std()
                vol_z = (rets.abs() - vol_std.rolling(20).mean()) / (vol_std.rolling(20).std() + 1e-9)
                vol_ratio = df['Volume'] / (df['Volume'].rolling(20).mean() + 1e-9)
                ema_20 = df['Close'].ewm(span=20).mean()
                stretch = (df['Close'] - ema_20) / ema_20
                
                for i in range(20, len(df)-5):
                    # 元のパニック条件
                    if vol_z.iloc[i] > 3.0 and vol_ratio.iloc[i] > 5.0 and stretch.iloc[i] < -0.015:
                        entry_p = df['Close'].iloc[i]
                        # 決済（5足以内の最高値）
                        exit_p = df['Close'].iloc[i+1:i+6].max()
                        pnl_clean = (exit_p / entry_p) - 1
                        
                        # ハードテスト: スリッページ 0.2% + 1分遅延(次の足のOpen)
                        entry_delayed = df['Open'].iloc[i+1] if i+1 < len(df) else entry_p
                        pnl_hard = (exit_p / (entry_delayed * 1.002)) - 1
                        
                        self.logs.append({
                            "ts": df.index[i], "ticker": ticker,
                            "vol_z": vol_z.iloc[i], "vol_ratio": vol_ratio.iloc[i], "stretch": stretch.iloc[i],
                            "pnl_clean": pnl_clean, "pnl_hard": pnl_hard
                        })
                        i += 10 # 重複回避

        self._report()

    def _report(self):
        if not self.logs: return
        df = pd.DataFrame(self.logs)
        print("\n" + "="*60)
        print("ALPHA DISSECTION REPORT (7 Trades Analysis)")
        print("="*60)
        for _, row in df.iterrows():
            status = "STABLE" if row['pnl_hard'] > 0 else "FRAGILE"
            print(f"{row['ts']} | {row['ticker']:7} | Z={row['vol_z']:.1f} | VolR={row['vol_ratio']:.1f} | PnL(Clean)={row['pnl_clean']*100:+.2f}% | PnL(Hard)={row['pnl_hard']*100:+.2f}% | [{status}]")
        
        print("-" * 60)
        print(f"Survival Rate (Hard Condition): {(df['pnl_hard'] > 0).mean()*100:.1f}%")
        print(f"Avg PnL (Hard): {df['pnl_hard'].mean()*100:.4f}%")
        print("="*60)

if __name__ == "__main__":
    from core import TICKER_LIST
    dissector = AlphaDissector(TICKER_LIST)
    dissector.dissect_panic(days=60)
