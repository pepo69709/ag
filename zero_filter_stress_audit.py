import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

# --- Sniper AI V114: Zero-Filter Stress Audit ---
# 役割: フィルタやレジーム判定を一切排除し、戦略の「核」だけの優位性を検証する。
# 目的: 極限の高コスト環境下でも、期待値がプラス（PF > 1.0）を維持できるかを確認する。

class ZeroFilterAuditor:
    def __init__(self, tickers):
        self.tickers = tickers
        # 往復 0.30% および 0.40% の「殺人的コスト」を設定
        self.costs = [0.002, 0.003, 0.004] 

    def run_stress_test(self):
        print(f"[*] Starting Zero-Filter Stress Audit (Stripping all filters...)")
        
        raw_results = {}
        for cost in self.costs:
            print(f"   [Process] Testing with Total Cost: {cost*100:.2f}%...")
            all_trades = []
            for t in self.tickers:
                try:
                    df = yf.download(t, period="2y", interval="60m", progress=False)
                    if len(df) < 200: continue
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    df.index = df.index.tz_localize(None)
                    
                    trades = self._simulate(df, cost)
                    all_trades.extend(trades)
                except: pass
            
            raw_results[cost] = all_trades

        self._report(raw_results)

    def _simulate(self, df, cost):
        # コア・ロジックのみ (Ticker-level Trend + Exhaustion)
        df['sma20'] = df['Close'].rolling(20).mean()
        df['sma50'] = df['Close'].rolling(50).mean()
        
        trades = []
        in_pos = False
        entry_p = 0
        
        for i in range(50, len(df)-1):
            # NO MARKET FILTER (Ignore ^N225)
            # Only Ticker conditions
            trend_ok = df['sma20'].iloc[i] > df['sma50'].iloc[i]
            exhaustion = df['Low'].iloc[i-2:i+1].min() >= df['Low'].iloc[i-3]
            
            if not in_pos and trend_ok and exhaustion:
                entry_p = df['Open'].iloc[i+1] * (1 + cost/2)
                in_pos = True
            elif in_pos:
                pnl = (df['Close'].iloc[i] / entry_p) - 1
                # Exit logic
                if pnl >= 0.03 or df['Close'].iloc[i] < (df['sma20'].iloc[i] * 0.98):
                    trades.append(pnl - cost/2)
                    in_pos = False
        return trades

    def _report(self, results):
        print("\n" + "="*60)
        print("ZERO-FILTER STRESS AUDIT: THE FINAL TRUTH")
        print("="*60)
        print(f"{'Total Cost (%)':<15} | {'PF':<8} | {'Trades':<8} | {'Status'}")
        print("-" * 60)
        
        for cost, trades in results.items():
            if not trades: continue
            arr = np.array(trades)
            wins = arr[arr > 0]
            losses = arr[arr <= 0]
            pf = sum(wins) / (abs(sum(losses)) + 1e-9)
            
            status = "SOVEREIGN" if pf >= 1.10 else ("ROBUST" if pf > 1.0 else "FAILED")
            print(f"{cost*100:13.2f}% | {pf:8.3f} | {len(trades):8} | {status}")
            
        print("="*60)
        print("Conclusion: If PF > 1.0 at 0.30%+, the core logic is structurally valid.")
        print("="*60)

if __name__ == "__main__":
    from core import TICKER_LIST
    auditor = ZeroFilterAuditor(TICKER_LIST)
    auditor.run_stress_test()
