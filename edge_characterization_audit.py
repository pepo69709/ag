import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

# --- Sniper AI V116: Edge Characterization Audit ---
# 役割: 戦略を「選択型(Selective)」と「頻度型(Frequency)」に分かち、
#       コスト耐性と最終的な期待値を比較する。

class CharacterAuditor:
    def __init__(self, tickers, cost=0.002):
        self.tickers = tickers
        self.cost = cost

    def run_audit(self):
        print(f"[*] Starting Edge Characterization Audit (Cost: {self.cost*100:.2f}%)")
        
        results = {}
        # 性格の定義
        profiles = {
            "SELECTIVE (Threshold 0.85)": {"threshold": 0.85, "tp": 0.03},
            "BALANCED (Current 0.65)": {"threshold": 0.65, "tp": 0.03},
            "FREQUENCY (Turnover Focused)": {"threshold": 0.60, "tp": 0.015}
        }
        
        for name, config in profiles.items():
            print(f"   [Profile] Testing: {name}...")
            all_trades = []
            for t in self.tickers:
                try:
                    df = yf.download(t, period="2y", interval="60m", progress=False)
                    if len(df) < 200: continue
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    df.index = df.index.tz_localize(None)
                    
                    trades = self._simulate(df, config)
                    all_trades.extend(trades)
                except: pass
            results[name] = all_trades

        self._report(results)

    def _simulate(self, df, config):
        df['sma20'] = df['Close'].rolling(20).mean()
        df['sma50'] = df['Close'].rolling(50).mean()
        
        trades = []
        in_pos = False
        entry_p = 0
        
        for i in range(50, len(df)-1):
            # コア・ロジック
            trend_ok = df['sma20'].iloc[i] > df['sma50'].iloc[i]
            exhaustion = df['Low'].iloc[i-2:i+1].min() >= df['Low'].iloc[i-3]
            
            # スコアリング (簡易版Tanh)
            ts_val = (df['sma20'].iloc[i] - df['sma50'].iloc[i]) / df['sma50'].iloc[i]
            score = np.tanh(ts_val * 40)
            
            if not in_pos and trend_ok and exhaustion and score >= config['threshold']:
                entry_p = df['Open'].iloc[i+1] * (1 + self.cost/2)
                in_pos = True
            elif in_pos:
                pnl = (df['Close'].iloc[i] / entry_p) - 1
                # Exit
                if pnl >= config['tp'] or df['Close'].iloc[i] < (df['sma20'].iloc[i] * 0.98):
                    trades.append(pnl - self.cost/2)
                    in_pos = False
        return trades

    def _report(self, results):
        print("\n" + "="*75)
        print("CHARACTERIZATION REPORT: SELECTIVE VS FREQUENCY")
        print("="*75)
        print(f"{'Profile':<30} | {'PF':<8} | {'Trades':<8} | {'Avg PnL':<10} | {'Expectancy'}")
        print("-" * 75)
        
        for name, trades in results.items():
            if not trades: continue
            arr = np.array(trades)
            pf = sum(arr[arr > 0]) / (abs(sum(arr[arr <= 0])) + 1e-9)
            avg_pnl = arr.mean() * 100
            expectancy = pf * len(trades) # 簡易スコア
            
            status = "ELITE" if pf >= 1.15 else ("VALID" if pf > 1.0 else "FAILED")
            print(f"{name:<30} | {pf:8.3f} | {len(trades):8} | {avg_pnl:>+8.2f}% | {status}")
            
        print("="*75)
        print("Decision: Higher PF on Selective means the edge needs 'Concentration'.")
        print("="*75)

if __name__ == "__main__":
    from core import TICKER_LIST
    auditor = CharacterAuditor(TICKER_LIST)
    auditor.run_audit()
