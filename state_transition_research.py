import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V37.0: State Transition Research ---
# 役割: 衝撃直後のカオスを無視し、5分後〜15分後の「状態遷移」にエッジがあるか検証する。
# 目的: 「直後」のギャンブルを卒業し、「遅延した秩序」を利益に変える。

class StateTransitionResearch:
    def __init__(self, tickers):
        self.tickers = tickers
        self.transitions = []

    def run_research(self, days=7):
        print(f"[*] Analyzing state transitions (T+5m to T+15m) after disruption...")
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
                high_low = df['High'] - df['Low']
                tr = pd.concat([high_low, (df['High'] - df['Close'].shift(1)).abs(), (df['Low'] - df['Close'].shift(1)).abs()], axis=1).max(axis=1)
                atr = tr.rolling(20).mean()
                vol_avg = df['Volume'].rolling(20).mean()
                
                for i in range(20, len(df)-20):
                    curr_move = df['Close'].iloc[i] - df['Close'].shift(1).iloc[i]
                    if abs(curr_move) > (atr.iloc[i] * 3.5) and df['Volume'].iloc[i] > (vol_avg.iloc[i] * 10.0) and curr_move < 0:
                        
                        # --- T+5分時点の状態を観測 ---
                        p_shock = df['Close'].iloc[i]
                        p_t5 = df['Close'].iloc[i+5]
                        
                        # 衝撃から5分間の挙動 (戻ったか、さらに掘ったか)
                        drift_5m = (p_t5 / p_shock) - 1
                        vol_5m = df['Volume'].iloc[i+1:i+6].mean() / df['Volume'].iloc[i]
                        
                        # --- T+5分からT+15分までの「結果」を観測 ---
                        # これがターゲット(PnL)
                        p_t15 = df['Close'].iloc[i+15]
                        future_pnl = (p_t15 / p_t5) - 1
                        
                        self.transitions.append({
                            "ts": df.index[i], "ticker": ticker,
                            "drift_5m": drift_5m,
                            "vol_5m": vol_5m,
                            "future_pnl": future_pnl
                        })
                        i += 20

        self._analyze_transitions()

    def _analyze_transitions(self):
        if not self.transitions: return
        df = pd.DataFrame(self.transitions)
        
        print("\n" + "="*70)
        print("STATE TRANSITION ANALYSIS (T+5m -> T+15m)")
        print("="*70)
        
        # 衝撃後5分間の状態でグループ分け
        # 1. さらに掘った (Drift < -0.1%)
        # 2. 横ばい (-0.1% < Drift < 0.1%)
        # 3. 反発し始めた (Drift > 0.1%)
        
        df['state'] = pd.cut(df['drift_5m'], bins=[-np.inf, -0.001, 0.001, np.inf], labels=['FURTHER_DROP', 'SIDEWAYS', 'REBOUNDING'])
        
        summary = df.groupby('state').agg({
            'future_pnl': ['mean', 'count', lambda x: (x > 0).mean()]
        })
        summary.columns = ['Avg_PnL', 'Count', 'WinRate']
        
        print(summary)
        print("-" * 70)
        print("Conclusion: Which state at T+5m leads to a tradeable edge at T+15m?")
        print("="*70)

if __name__ == "__main__":
    from core import TICKER_LIST
    tester = StateTransitionResearch(TICKER_LIST)
    tester.run_research(days=7)
