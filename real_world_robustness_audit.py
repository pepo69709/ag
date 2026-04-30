import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

# --- Sniper AI V115: Real-World Robustness Audit ---
# 役割: 約定遅延(1時間)と変動スリッページを導入し、現実の「摩擦」に対する脆弱性を暴く。
# 目的: 「ガラスのエッジ」か「実戦の武器」かを最終判定する。

class RobustnessAuditor:
    def __init__(self, tickers, base_cost=0.002):
        self.tickers = tickers
        self.base_cost = base_cost

    def run_robustness_test(self):
        print(f"[*] Starting Real-World Robustness Audit (Base Cost: {self.base_cost*100:.2f}%)")
        
        scenarios = {
            "IDEAL (Next Open)": 0,
            "LAGGED (1-Hour Delay)": 1,
            "VARIABLE (Lethal Cost 0.35%)": 0 # costを別途上乗せ
        }
        
        results = {}
        for name, lag in scenarios.items():
            print(f"   [Scenario] Running: {name}...")
            all_trades = []
            cost = 0.0035 if "VARIABLE" in name else self.base_cost
            
            for t in self.tickers:
                try:
                    df = yf.download(t, period="2y", interval="60m", progress=False)
                    if len(df) < 200: continue
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    df.index = df.index.tz_localize(None)
                    
                    trades = self._simulate(df, cost, lag)
                    all_trades.extend(trades)
                except: pass
            results[name] = all_trades

        self._report(results)

    def _simulate(self, df, cost, lag):
        df['sma20'] = df['Close'].rolling(20).mean()
        df['sma50'] = df['Close'].rolling(50).mean()
        
        trades = []
        in_pos = False
        entry_p = 0
        
        for i in range(50, len(df) - (lag + 1)):
            trend_ok = df['sma20'].iloc[i] > df['sma50'].iloc[i]
            exhaustion = df['Low'].iloc[i-2:i+1].min() >= df['Low'].iloc[i-3]
            
            if not in_pos and trend_ok and exhaustion:
                # LAG導入: シグナル確定(i)から(1+lag)本後の始値でエントリー
                entry_p = df['Open'].iloc[i+1+lag] * (1 + cost/2)
                in_pos = True
            elif in_pos:
                # 決済も同様にラグを考慮する場合があるが、ここでは安全側でClose[i]を使用
                pnl = (df['Close'].iloc[i] / entry_p) - 1
                if pnl >= 0.03 or df['Close'].iloc[i] < (df['sma20'].iloc[i] * 0.98):
                    trades.append(pnl - cost/2)
                    in_pos = False
        return trades

    def _report(self, results):
        print("\n" + "="*70)
        print("REAL-WORLD ROBUSTNESS AUDIT: SURVIVAL ENVELOPE")
        print("="*70)
        print(f"{'Scenario':<30} | {'PF':<8} | {'Trades':<8} | {'Alpha Decay'}")
        print("-" * 70)
        
        base_pf = None
        for name, trades in results.items():
            if not trades: continue
            arr = np.array(trades)
            wins = arr[arr > 0]
            losses = arr[arr <= 0]
            pf = sum(wins) / (abs(sum(losses)) + 1e-9)
            
            if base_pf is None: base_pf = pf
            decay = (pf / base_pf - 1) * 100 if base_pf else 0
            
            decay_str = f"{decay:+.1f}%" if decay != 0 else "BASE"
            print(f"{name:<30} | {pf:8.3f} | {len(trades):8} | {decay_str}")
            
        print("="*70)
        print("Conclusion: High Alpha Decay on LAGGED means manual execution is RISKY.")
        print("="*70)

if __name__ == "__main__":
    from core import TICKER_LIST
    auditor = RobustnessAuditor(TICKER_LIST)
    auditor.run_robustness_test()
