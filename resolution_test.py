import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V33.0: Resolution Test ---
# 役割: 5分足では見えなかった「瞬間の真空(Vacuum)」が1分足で可視化されるか検証。
# 手法: 1分足データを用い、衝撃直後(1-3分)の価格再構築プロセスを解剖する。

class ResolutionTest:
    def __init__(self, tickers):
        self.tickers = tickers
        self.events = []

    def run_1m_test(self, days=7): # 1分足は期間制限があるため7日間
        print(f"[*] Shifting resolution to 1 minute over {days} days...")
        interval = "1m"
        data = yf.download(self.tickers, period=f"{days}d", interval=interval, group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        all_dates = data.index.normalize().unique()
        for date in all_dates:
            day_data = data[data.index.normalize() == date]
            for ticker in self.tickers:
                df = day_data[ticker]
                if len(df) < 60: continue
                
                # 1分足での異常検知 (ATR 3倍 / Vol 8倍)
                high_low = df['High'] - df['Low']
                tr = pd.concat([high_low, (df['High'] - df['Close'].shift(1)).abs(), (df['Low'] - df['Close'].shift(1)).abs()], axis=1).max(axis=1)
                atr = tr.rolling(20).mean()
                vol_avg = df['Volume'].rolling(20).mean()
                
                for i in range(20, len(df)-10):
                    curr_move = df['Close'].iloc[i] - df['Close'].shift(1).iloc[i]
                    # 1分足での衝撃
                    if abs(curr_move) > (atr.iloc[i] * 3.5) and df['Volume'].iloc[i] > (vol_avg.iloc[i] * 10.0) and curr_move < 0:
                        entry_p = df['Close'].iloc[i]
                        
                        # 直後の1分〜5分を詳細に追跡
                        recovery_1m = (df['Close'].iloc[i+1] / entry_p) - 1
                        recovery_3m = (df['Close'].iloc[i+3] / entry_p) - 1
                        recovery_5m = (df['Close'].iloc[i+5] / entry_p) - 1
                        
                        self.events.append({
                            "ts": df.index[i], "ticker": ticker,
                            "rec1": recovery_1m, "rec3": recovery_3m, "rec5": recovery_5m,
                            "move_atr": abs(curr_move)/atr.iloc[i]
                        })
                        i += 15 # 重複回避

        self._report()

    def _report(self):
        if not self.events: 
            print("[!] No events found with current 1m criteria. Disruption is rarer at this scale.")
            return
        df = pd.DataFrame(self.events)
        print("\n" + "="*75)
        print("1-MINUTE RESOLUTION ANALYSIS")
        print("="*75)
        for _, row in df.iterrows():
            # 1分後の挙動でタイプ判定
            etype = "VACUUM (V)" if row['rec1'] > 0.001 else ("DRIFT (L)" if row['rec1'] < -0.001 else "STAGNANT (-)")
            print(f"{row['ts']} | {row['ticker']:7} | Rec1m={row['rec1']*100:+.2f}% | Rec3m={row['rec3']*100:+.2f}% | ATR_X={row['move_atr']:.1f} | Type: {etype}")
        print("-" * 75)
        print(f"Total Disruption Events (1m): {len(df)}")
        print(f"Immediate Rebound Rate (Rec1m > 0): {(df['rec1'] > 0).mean()*100:.1f}%")
        print("="*75)

if __name__ == "__main__":
    from core import TICKER_LIST
    tester = ResolutionTest(TICKER_LIST)
    tester.run_1m_test(days=7)
