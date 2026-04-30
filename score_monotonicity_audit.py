import pandas as pd
import numpy as np
import yfinance as yf

# --- Sniper AI V81.0: Monotonicity Audit ---
# 役割: スコア(収縮度+回復度)とリターンの相関を分析し、エッジの「太さ」を検証する。
# 目的: 閾値依存を排除し、スコアが高いほど期待値が向上する「単調増加」を証明する。

class MonotonicityAudit:
    def __init__(self, tickers):
        self.tickers = tickers
        self.trade_records = []

    def run_audit(self, years=1):
        print(f"[*] Auditing score monotonicity over {years} year(s)...")
        data = yf.download(self.tickers, period=f"{years}y", interval="60m", group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        for ticker in self.tickers:
            df = data[ticker].dropna()
            if len(df) < 100: continue
            
            # 指標
            df['sma20'] = df['Close'].rolling(20).mean()
            df['sma50'] = df['Close'].rolling(50).mean()
            
            for i in range(50, len(df)-20):
                # 衝撃 + 沈黙 + 枯渇
                if df['sma20'].iloc[i] > df['sma50'].iloc[i] and df['Low'].iloc[i] < (df['sma20'].iloc[i] * 1.01):
                    if i >= 3 and df['Low'].iloc[i-2:i+1].min() >= df['Low'].iloc[i-3]:
                        
                        # --- スコアリング ---
                        # 1. 収縮度 (0.005が最高、0.02が最低)
                        comp = (df['High'].iloc[i-2:i+1].max() / df['Low'].iloc[i-2:i+1].min()) - 1
                        s_comp = np.clip((0.02 - comp) / 0.015, 0, 1)
                        
                        # 2. 回復度 (RSI 45-60を理想とする)
                        rsi = self._rsi(df['Close'].iloc[i-20:i+1])
                        s_rsi = 1.0 - np.clip(abs(rsi - 50) / 20, 0, 1) # 50に近いほど1
                        
                        total_score = s_comp + s_rsi
                        
                        # 3. リターンの記録 (固定エグジット 3% or 2%損切り)
                        entry_p = df['Open'].iloc[i+1] * 1.001
                        # 簡易シミュレーション
                        pnl = 0
                        for k in range(i+1, i+20):
                            if k >= len(df): break
                            curr_p = df['Close'].iloc[k]
                            pnl_raw = (curr_p / entry_p) - 1
                            if pnl_raw >= 0.03:
                                pnl = 0.03 - 0.001
                                break
                            if curr_p < (df['sma20'].iloc[k] * 0.98):
                                pnl = pnl_raw - 0.001
                                break
                            pnl = pnl_raw - 0.001 # タイムアウト

                        self.trade_records.append({"Score": total_score, "PnL": pnl})
                        i += 10

        self._report_monotonicity()

    def _rsi(self, series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-9)
        return 100 - (100 / (1 + rs.iloc[-1]))

    def _report_monotonicity(self):
        df = pd.DataFrame(self.trade_records)
        if df.empty: return
        
        # スコアでソート
        df = df.sort_values("Score", ascending=False)
        
        print("\n" + "="*70)
        print("MONOTONICITY AUDIT: SCORE vs PERFORMANCE")
        print("="*70)
        print(f"{'Quantile':12} | {'Count':6} | {'Avg PnL':10} | {'PF':8}")
        print("-" * 50)
        
        quantiles = [0.1, 0.2, 0.3, 0.5, 1.0]
        for q in quantiles:
            subset = df.head(int(len(df) * q))
            pnl_avg = subset['PnL'].mean() * 100
            pf = sum([p for p in subset['PnL'] if p > 0]) / (abs(sum([p for p in subset['PnL'] if p <= 0])) + 1e-9)
            print(f"Top {int(q*100):3}%      | {len(subset):6} | {pnl_avg:+.3f}%   | {pf:.4f}")
        
        print("="*70)
        print("Analysis: Is the performance increasing with the score?")
        print("="*70)

if __name__ == "__main__":
    from core import TICKER_LIST
    audit = MonotonicityAudit(TICKER_LIST)
    audit.run_audit(years=1)
