import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import os

# --- Sniper AI V1.0: Eternal Bone (Rakuten Zero Edition) ---
# 役割: 最高の頑健性を誇る純物理ロジック。
# 特徴: 楽天証券の手数料無料を活かし、微小なエッジを確実に利益へ変える。

class EternalBone:
    def __init__(self, tickers):
        self.tickers = tickers
        self.positions = []
        self.trade_history = []
        self.sl_k = 2.0
        self.base_trail_k = 1.0
        self.max_mins = 180
        self.cost_ratio = 0.0002 # 楽天証券手数料無料 + スプレッド想定

    def run_backtest(self, days=60):
        print(f"[*] Final Victory Run V1.0 (60d Pure Physical): {days} days...")
        interval = "5m"
        data = yf.download(self.tickers, period="60d", interval=interval, group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        all_dates = data.index.normalize().unique()
        for date in all_dates:
            day_data = data[data.index.normalize() == date]
            if len(day_data) < 50: continue
            
            timestamps = day_data.index
            for i in range(50, len(timestamps)):
                self._update_and_check_exits(day_data, i, timestamps[i])
                self._check_entries(day_data, i, timestamps[i])

        self._analyze_results()

    def _check_entries(self, data, idx, ts):
        if len(self.positions) >= 5: return
        candidates = []
        for ticker in self.tickers:
            if ticker in [p['ticker'] for p in self.positions]: continue
            try:
                df_slice = data[ticker].iloc[idx-50:idx]
                close = df_slice['Close'].iloc[-1]; vol = df_slice['Close'].pct_change().rolling(20).std().iloc[-1]
                high_10 = df_slice['High'].rolling(10).max().iloc[-1]
                pb_ratio = ((high_10 - close) / (high_10 + 1e-9)) / (vol + 1e-9)
                
                if pb_ratio < 0.8 or vol < 0.003: continue
                
                pb_score = np.exp(-((pb_ratio - 2.5) ** 2) / (2 * 1.5 ** 2))
                if pb_score > 0.72 and df_slice['Close'].pct_change(1).iloc[-1] > 0:
                    candidates.append({"ticker": ticker, "price": close, "score": pb_score, "pb_ratio": pb_ratio,
                                       "atr": (df_slice['High'] - df_slice['Low']).rolling(20).mean().iloc[-1]})
            except: continue
        
        candidates = sorted(candidates, key=lambda x: x['score'], reverse=True)
        for cand in candidates[:(5 - len(self.positions))]:
            self.positions.append({"ticker": cand["ticker"], "entry_price": cand["price"], "entry_ts": ts,
                                   "entry_atr": cand["atr"], "highest_price": cand["price"], "pb_ratio": cand["pb_ratio"]})

    def _update_and_check_exits(self, data, idx, ts):
        active_positions = []
        for pos in self.positions:
            ticker = pos["ticker"]; curr_price = data[ticker]['Close'].iloc[idx]
            if np.isnan(curr_price): active_positions.append(pos); continue
            if curr_price > pos["highest_price"]: pos["highest_price"] = curr_price
            
            pnl = (curr_price / pos["entry_price"]) - 1
            trail_k = self.base_trail_k * np.clip(pos["pb_ratio"] / 3.0, 0.5, 1.5) * np.clip(pnl / 0.02, 0.8, 2.0)
            
            if curr_price <= pos["entry_price"] - (pos["entry_atr"] * self.sl_k) or \
               (curr_price <= pos["highest_price"] - (pos["entry_atr"] * trail_k) and pos["highest_price"] > pos["entry_price"]) or \
               (ts - pos["entry_ts"]).total_seconds() / 60 >= self.max_mins:
                self.trade_history.append({"pnl": pnl - self.cost_ratio})
            else: active_positions.append(pos)
        self.positions = active_positions

    def _analyze_results(self):
        if not self.trade_history: return
        df = pd.DataFrame(self.trade_history)
        pf = df[df['pnl']>0]['pnl'].sum() / (abs(df[df['pnl']<=0]['pnl'].sum()) + 1e-9)
        print(f"\n--- Sniper AI V1.0 Eternal Bone (Final) ---")
        print(f"Total Trades: {len(df)} | Win Rate: {(df['pnl']>0).mean()*100:.2f}% | PF: {pf:.4f} | Net Ret: {df['pnl'].sum()*100:.2f}%")

if __name__ == "__main__":
    from core import TICKER_LIST
    tester = EternalBone(TICKER_LIST)
    tester.run_backtest(days=60)
