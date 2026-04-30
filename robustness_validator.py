import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V56.0: Robustness Validator ---
# 役割: 戦略のパラメータを揺さぶり、結果の安定性(Robustness)を検証する。
# 目的: 特定の数値への依存を排し、「構造的なエッジ」であることを証明する。

class RobustnessValidator:
    def __init__(self, tickers):
        self.tickers = tickers
        self.all_trades = []

    def run_validation(self, days=7):
        print(f"[*] Shaking the strategy parameters over {days} days...")
        interval = "1m"
        data = yf.download(self.tickers, period=f"{days}d", interval=interval, group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        # パラメータセット (待機時間, 沈黙閾値)
        param_grid = [
            (2, 0.0008), (3, 0.0010), (4, 0.0012)
        ]
        
        results_grid = {}
        
        for wait_m, threshold in param_grid:
            trades = []
            for ticker in self.tickers:
                df = data[ticker]
                if len(df) < 60: continue
                
                tr = pd.concat([(df['High']-df['Low']), (df['High']-df['Close'].shift(1)).abs()], axis=1).max(axis=1)
                atr = tr.rolling(20).mean()
                vol_avg = df['Volume'].rolling(20).mean()
                
                for i in range(20, len(df)-25):
                    if (df['Close'].iloc[i] - df['Close'].shift(1).iloc[i]) < -(atr.iloc[i] * 3.5) and df['Volume'].iloc[i] > (vol_avg.iloc[i] * 10.0):
                        
                        # 待機・沈黙・枯渇のチェック
                        wait_win = df.iloc[i+1:i+wait_m+1]
                        recovery = (wait_win['Close'].iloc[-1] / df['Close'].iloc[i]) - 1
                        no_new_low = wait_win['Low'].min() >= df['Low'].iloc[i]
                        # 追加: ボリュームディケイ (出来高激減)
                        vol_decay = wait_win['Volume'].mean() < (df['Volume'].iloc[i] * 0.2)
                        
                        if recovery < threshold and no_new_low and vol_decay:
                            entry_p = df['Open'].iloc[i+wait_m+1] * 1.001
                            exit_p = df['Close'].iloc[i+wait_m+11] if i+wait_m+11 < len(df) else df['Close'].iloc[-1]
                            pnl = (exit_p / entry_p) - 1
                            trades.append(pnl)
                        i += 20
            
            if trades:
                results_grid[f"W:{wait_m}, T:{threshold*100:.2f}%"] = {
                    "PF": sum([p for p in trades if p > 0]) / (abs(sum([p for p in trades if p <= 0])) + 1e-9),
                    "WinRate": (np.array(trades) > 0).mean(),
                    "Count": len(trades)
                }

        self._report(results_grid)

    def _report(self, grid):
        print("\n" + "="*70)
        print("ROBUSTNESS VALIDATION REPORT (Sensitivity Test)")
        print("="*70)
        for params, res in grid.items():
            print(f"Params: {params:15} | PF: {res['PF']:.3f} | WinRate: {res['WinRate']*100:.1f}% | Count: {res['Count']}")
        
        print("-" * 70)
        print("Conclusion: Is the edge stable across parameters?")
        print("="*70)

if __name__ == "__main__":
    from core import TICKER_LIST
    validator = RobustnessValidator(TICKER_LIST)
    validator.run_validation(days=7)
