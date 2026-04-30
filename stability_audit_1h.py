import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V74.0: Stability Audit ---
# 役割: 1年間のバックテスト結果を「前半」と「後半」に分割し、エッジの再現性を検証する。
# 目的: 特定の期間の幸運(過学習)を排し、通年で機能する「本物の構造」であることを証明する。

class StabilityAudit:
    def __init__(self, tickers):
        self.tickers = tickers
        self.all_trades = []

    def run_audit(self, total_years=1):
        print(f"[*] Auditing stability by splitting {total_years} year(s) into two periods...")
        data = yf.download(self.tickers, period=f"{total_years}y", interval="60m", group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        # 期間の分割点を計算
        split_date = data.index[len(data)//2]
        print(f"[*] Split Date: {split_date}")
        
        periods = {
            "First 6 Months": data[data.index < split_date],
            "Last 6 Months": data[data.index >= split_date]
        }
        
        overall_results = {}
        
        for name, p_data in periods.items():
            trades = []
            for ticker in self.tickers:
                df = p_data[ticker].dropna()
                if len(df) < 100: continue
                
                df['sma20'] = df['Close'].rolling(20).mean()
                df['sma50'] = df['Close'].rolling(50).mean()
                
                in_position = False
                entry_p = 0
                
                for i in range(50, len(df)-20):
                    trend_ok = df['sma20'].iloc[i] > df['sma50'].iloc[i]
                    is_dip = df['Low'].iloc[i] < (df['sma20'].iloc[i] * 1.01)
                    
                    if not in_position and trend_ok and is_dip:
                        # 3時間の枯渇
                        if i >= 3 and df['Low'].iloc[i-2:i+1].min() >= df['Low'].iloc[i-3]:
                            entry_p = df['Open'].iloc[i+1] * 1.001
                            in_position = True
                    
                    elif in_position:
                        current_p = df['Close'].iloc[i]
                        pnl = (current_p / entry_p) - 1
                        if pnl >= 0.03 or current_p < (df['sma20'].iloc[i] * 0.98):
                            trades.append(pnl - 0.001)
                            in_position = False
            
            if trades:
                trades_arr = np.array(trades)
                pf = sum([p for p in trades_arr if p > 0]) / (abs(sum([p for p in trades_arr if p <= 0])) + 1e-9)
                overall_results[name] = {
                    "PF": pf,
                    "WinRate": (trades_arr > 0).mean() * 100,
                    "Avg_PnL": trades_arr.mean() * 100,
                    "Count": len(trades)
                }

        self._report(overall_results)

    def _report(self, results):
        print("\n" + "="*70)
        print("STABILITY AUDIT REPORT (Split-Period Validation)")
        print("="*70)
        for name, res in results.items():
            print(f"[{name}]")
            print(f"  Trades  : {res['Count']}")
            print(f"  PF      : {res['PF']:.4f}")
            print(f"  WinRate : {res['WinRate']:.1f}%")
            print(f"  Avg PnL : {res['Avg_PnL']:+.3f}%")
            print("-" * 35)
        
        print("Conclusion: Is the edge consistent across both halves?")
        print("="*70)

if __name__ == "__main__":
    from core import TICKER_LIST
    audit = StabilityAudit(TICKER_LIST)
    audit.run_audit(total_years=1)
