import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V54.0: Exhaustion Research ---
# 役割: 「沈黙(Recovery < 0.1%)」の中に隠れた「安値更新の有無」が、反発の勝率にどう影響するか検証。
# 目的: 単なる横ばいから、「売りの枯渇(Exhaustion)」という確証されたエントリーへ進化させる。

class ExhaustionResearch:
    def __init__(self, tickers):
        self.tickers = tickers
        self.results = []

    def run_research(self, days=7):
        print(f"[*] Analyzing 'Exhaustion' signs (No New Low) during silence...")
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
                tr = pd.concat([(df['High']-df['Low']), (df['High']-df['Close'].shift(1)).abs()], axis=1).max(axis=1)
                atr = tr.rolling(20).mean()
                vol_avg = df['Volume'].rolling(20).mean()
                
                for i in range(20, len(df)-20):
                    if (df['Close'].iloc[i] - df['Close'].shift(1).iloc[i]) < -(atr.iloc[i] * 3.5) and df['Volume'].iloc[i] > (vol_avg.iloc[i] * 10.0):
                        
                        # 衝撃の安値と終値
                        low_shock = df['Low'].iloc[i]
                        p_shock = df['Close'].iloc[i]
                        
                        # 3分間の「沈黙」チェック
                        wait_window = df.iloc[i+1:i+4]
                        recovery_3m = (wait_window['Close'].iloc[-1] / p_shock) - 1
                        
                        # 特徴量: 安値更新の有無
                        lowest_during_wait = wait_window['Low'].min()
                        made_new_low = 1 if lowest_during_wait < low_shock else 0
                        
                        # 実際の結果 (3分後から10分保持)
                        entry_p = df['Open'].iloc[i+4] * 1.001
                        exit_p = df['Close'].iloc[i+14] if i+14 < len(df) else df['Close'].iloc[-1]
                        pnl = (exit_p / entry_p) - 1
                        
                        # 「沈黙(Recovery < 0.1%)」している個体のみを対象に分類
                        if recovery_3m < 0.001:
                            self.results.append({
                                "ts": df.index[i], "ticker": ticker,
                                "made_new_low": made_new_low,
                                "pnl": pnl
                            })
                        i += 20

        self._analyze_results()

    def _analyze_results(self):
        if not self.results: return
        df = pd.DataFrame(self.results)
        
        print("\n" + "="*70)
        print("EXHAUSTION ANALYSIS (Silent Period Breakdown)")
        print("="*70)
        print(f"Total Silent Events: {len(df)}")
        
        # 安値更新の有無によるグループ分け
        summary = df.groupby('made_new_low').agg({
            'pnl': ['mean', 'count', lambda x: (x > 0).mean()]
        })
        summary.columns = ['Avg_PnL', 'Count', 'WinRate']
        summary.index = ['NO_NEW_LOW (Exhaustion)', 'MADE_NEW_LOW (Still Selling)']
        
        print(summary)
        print("-" * 70)
        print("Conclusion: Did 'No New Low' confirm the sellers' exhaustion?")
        print("="*70)

if __name__ == "__main__":
    from core import TICKER_LIST
    tester = ExhaustionResearch(TICKER_LIST)
    tester.run_research(days=7)
