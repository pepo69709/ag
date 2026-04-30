import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import random

# --- Sniper AI V27.0: Chaos Engine (Stress Test) ---
# 役割: 完璧なバックテストを「破壊」し、真のロバストネスを測定する。
# 手法: ランダムスリッページ注入 + ウォークフォワード的な期間スライス。

class ChaosEngine:
    def __init__(self, tickers):
        self.tickers = tickers
        self.results = []

    def run_stress_test(self, days=60, iterations=10):
        print(f"[*] Starting Stress Test (Monte Carlo Slippage & Jitter)...")
        interval = "5m"
        data = yf.download(self.tickers, period=f"{days}d", interval=interval, group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        all_dates = data.index.normalize().unique()
        
        for it in range(iterations):
            trade_history = []
            # ランダムなコスト変動 (0.05% - 0.25%)
            dynamic_cost = random.uniform(0.0005, 0.0025) 
            
            positions = []
            for date in all_dates:
                day_data = data[data.index.normalize() == date]
                if len(day_data) < 50: continue
                
                timestamps = day_data.index
                for i in range(50, len(timestamps)):
                    # 1. エグジット処理
                    active_positions = []
                    for pos in positions:
                        ticker = pos["ticker"]; curr_price = day_data[ticker]['Close'].iloc[i]
                        if np.isnan(curr_price): active_positions.append(pos); continue
                        if curr_price > pos["highest_price"]: pos["highest_price"] = curr_price
                        
                        pnl = (curr_price / pos["entry_price"]) - 1
                        trail_k = 1.0 * np.clip(pos["pb_ratio"] / 3.0, 0.5, 1.5) * np.clip(pnl / 0.02, 0.8, 2.0)
                        
                        if curr_price <= pos["entry_price"] - (pos["entry_atr"] * 2.0) or \
                           (curr_price <= pos["highest_price"] - (pos["entry_atr"] * trail_k) and pos["highest_price"] > pos["entry_price"]) or \
                           (timestamps[i] - pos["entry_ts"]).total_seconds() / 60 >= 180:
                            # 決済。ここでランダムなスリッページを更に追加
                            final_slip = random.uniform(-0.001, 0.001)
                            trade_history.append({"pnl": pnl - dynamic_cost + final_slip})
                        else: active_positions.append(pos)
                    positions = active_positions
                    
                    # 2. エントリー処理
                    if len(positions) < 5:
                        for ticker in self.tickers:
                            if any(p["ticker"] == ticker for p in positions): continue
                            try:
                                df_slice = day_data[ticker].iloc[i-50:i]
                                close = df_slice['Close'].iloc[-1]; vol = df_slice['Close'].pct_change().rolling(20).std().iloc[-1]
                                high_10 = df_slice['High'].rolling(10).max().iloc[-1]
                                pb_ratio = ((high_10 - close) / (high_10 + 1e-9)) / (vol + 1e-9)
                                
                                # 物理フィルタ
                                if pb_ratio >= 0.8 and vol >= 0.003:
                                    pb_score = np.exp(-((pb_ratio - 2.5) ** 2) / (2 * 1.5 ** 2))
                                    if pb_score > 0.72 and df_slice['Close'].pct_change(1).iloc[-1] > 0:
                                        # 1分遅延（次の足のOpenで約定と仮定）を模して、少し価格を滑らせる
                                        slip_entry = random.uniform(0.0002, 0.001) # 0.02%-0.1% 高く買わされる
                                        positions.append({
                                            "ticker": ticker, "entry_price": close * (1 + slip_entry),
                                            "entry_ts": timestamps[i], "pb_ratio": pb_ratio,
                                            "highest_price": close, "entry_atr": (df_slice['High'] - df_slice['Low']).rolling(20).mean().iloc[-1]
                                        })
                            except: continue
            
            # イテレーション結果の集計
            if trade_history:
                df = pd.DataFrame(trade_history)
                pf = df[df['pnl']>0]['pnl'].sum() / (abs(df[df['pnl']<=0]['pnl'].sum()) + 1e-9)
                self.results.append(pf)
                print(f"Iteration {it+1}: PF = {pf:.4f} (Cost: {dynamic_cost*100:.3f}%)")

        self._report()

    def _report(self):
        if not self.results: return
        print("\n" + "="*40 + "\nSTRESS TEST FINAL REPORT\n" + "="*40)
        print(f"Average PF: {np.mean(self.results):.4f}")
        print(f"PF Standard Deviation: {np.std(self.results):.4f}")
        print(f"Probability of PF > 1.0: {(np.array(self.results) > 1.0).mean()*100:.2f}%")
        print("="*40)

if __name__ == "__main__":
    from core import TICKER_LIST
    engine = ChaosEngine(TICKER_LIST)
    engine.run_stress_test(days=60, iterations=10)
