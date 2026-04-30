import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V32.0: Event Classifier ---
# 役割: 14件のパニックイベントを「構造的」に分類し、真の利益源を特定する。
# 手法: 衝撃後の価格推移(Recovery Speed)と出来高の継続性(Volume Tail)によるクラスタリング。

class EventClassifier:
    def __init__(self, tickers):
        self.tickers = tickers
        self.events = []

    def classify_events(self, days=60):
        print(f"[*] Classifying market disruption events over {days} days...")
        interval = "5m"
        data = yf.download(self.tickers, period=f"{days}d", interval=interval, group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        all_dates = data.index.normalize().unique()
        for date in all_dates:
            day_data = data[data.index.normalize() == date]
            for ticker in self.tickers:
                df = day_data[ticker]
                if len(df) < 30: continue
                
                # 衝撃検知 (ATR 3倍 / Vol 8倍)
                high_low = df['High'] - df['Low']
                high_close = (df['High'] - df['Close'].shift(1)).abs()
                low_close = (df['Low'] - df['Close'].shift(1)).abs()
                tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                atr = tr.rolling(20).mean()
                vol_avg = df['Volume'].rolling(20).mean()
                
                for i in range(20, len(df)-10):
                    curr_move = df['Close'].iloc[i] - df['Close'].shift(1).iloc[i]
                    if abs(curr_move) > (atr.iloc[i] * 3.0) and df['Volume'].iloc[i] > (vol_avg.iloc[i] * 8.0) and curr_move < 0:
                        entry_p = df['Close'].iloc[i]
                        
                        # --- 分類用指標 ---
                        # 1. Recovery Speed (直後2本の戻り率)
                        next_2_close = df['Close'].iloc[i+2] if i+2 < len(df) else df['Close'].iloc[-1]
                        recovery_rate = (next_2_close - entry_p) / abs(curr_move)
                        
                        # 2. Volume Persistence (直後2本の出来高継続性)
                        vol_tail = df['Volume'].iloc[i+1:i+3].mean() / df['Volume'].iloc[i]
                        
                        # 3. 実際のPnL (15分後)
                        exit_p = df['Close'].iloc[i+3] if i+3 < len(df) else df['Close'].iloc[-1]
                        pnl = (exit_p / entry_p) - 1
                        
                        self.events.append({
                            "ts": df.index[i], "ticker": ticker,
                            "recovery": recovery_rate, "vol_tail": vol_tail,
                            "pnl": pnl, "move_atr": abs(curr_move)/atr.iloc[i]
                        })
                        i += 10

        self._report()

    def _report(self):
        if not self.events: return
        df = pd.DataFrame(self.events)
        print("\n" + "="*70)
        print("EVENT CLASSIFICATION REPORT")
        print("="*70)
        # 戻り率でソート
        df = df.sort_values(by="recovery", ascending=False)
        for _, row in df.iterrows():
            # 簡易クラスタ判定
            etype = "VACUUM (V)" if row['recovery'] > 0.5 else ("DRIFT (L)" if row['recovery'] < 0 else "STAGNANT (-)")
            print(f"{row['ts']} | {row['ticker']:7} | Recov={row['recovery']:+.2f} | VolTail={row['vol_tail']:.2f} | PnL={row['pnl']*100:+.2f}% | Type: {etype}")
        print("="*70)

if __name__ == "__main__":
    from core import TICKER_LIST
    classifier = EventClassifier(TICKER_LIST)
    classifier.classify_events(days=60)
