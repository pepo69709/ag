import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from core import TICKER_LIST

# --- V24.3 Diagnostic: Winner's Struggle Analysis ---
# 役割: 「最終的に勝ったトレード」が、初期(30分時点)でどれだけ含み損に耐えていたかを分析。

class WinnerAnalyzer:
    def __init__(self, tickers):
        self.tickers = tickers
        self.win_logs = []

    def run(self):
        print(f"[*] Analyzing Winner's Patterns in Graveyard Period...")
        end_date = datetime.now() - timedelta(days=30); start_date = datetime.now() - timedelta(days=59)
        data = yf.download(self.tickers, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), interval="5m", group_by='ticker', progress=False)
        
        for ticker in self.tickers:
            df = data[ticker]
            for i in range(50, len(df)-40):
                try:
                    df_slice = df.iloc[i-50:i]; close = df_slice['Close'].iloc[-1]
                    vol = df_slice['Close'].pct_change().rolling(20).std().iloc[-1]
                    high_10 = df_slice['High'].rolling(10).max().iloc[-1]
                    if ((high_10 - close) / (high_10 + 1e-9)) / (vol + 1e-9) >= 0.8:
                        future = df.iloc[i:i+36]
                        if future.empty: continue
                        final_pnl = (future['Close'].iloc[-1] / close) - 1
                        
                        # 最終的に勝ったトレードのみ
                        if final_pnl > 0.005: 
                            pnl_30m = (future['Close'].iloc[min(5, len(future)-1)] / close) - 1
                            self.win_logs.append({"pnl_30m": pnl_30m})
                except: continue
        self._report()

    def _report(self):
        if not self.win_logs: return
        df = pd.DataFrame(self.win_logs)
        print("\n" + "="*40 + "\nWINNER'S STRUGGLE REPORT\n" + "="*40)
        print(f"Total Win Samples: {len(df)}")
        print(f"Ratio of Winners that were NEGATIVE at 30m: {(df['pnl_30m'] < 0).mean()*100:.2f}%")
        print("="*40)

if __name__ == "__main__":
    WinnerAnalyzer(TICKER_LIST).run()
