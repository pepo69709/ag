import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from core import TICKER_LIST

# --- V19.8-OS: Physical Baseline (Out-of-Sample) ---
# 役割: 未知の期間(60d-30d ago)で物理ロジックのみを検証。

class PhysicalPredatorOS:
    def __init__(self, tickers):
        self.tickers = tickers
        self.positions = []
        self.trade_history = []
        self.sl_k = 2.0
        self.base_trail_k = 1.0
        self.max_mins = 180
        self.cost_ratio = 0.001

    def run(self):
        print(f"[*] Starting Physical Baseline (Out-of-Sample: 60d to 30d ago)...")
        end_date = datetime.now() - timedelta(days=30)
        start_date = datetime.now() - timedelta(days=59)
        data = yf.download(self.tickers, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), interval="5m", group_by='ticker', progress=False)
        
        timestamps = data.index
        for i in range(50, len(timestamps)):
            self._update_and_check_exits(data, i, timestamps[i])
            self._check_entries(data, i, timestamps[i])
        self._analyze()

    def _check_entries(self, data, idx, ts):
        if len(self.positions) >= 5: return
        all_rets = []
        for t in self.tickers:
            try:
                val = data[t]['Close'].pct_change(1).iloc[idx]
                if not np.isnan(val): all_rets.append(val)
            except: continue
        market_avg_ret = np.mean(all_rets) if all_rets else 0
        regime_boost = 1.1 if market_avg_ret > 0 else 0.8
        
        candidates = []
        for ticker in self.tickers:
            if ticker in [p['ticker'] for p in self.positions]: continue
            try:
                df_slice = data[ticker].iloc[idx-50:idx]
                if df_slice.isnull().values.any(): continue
                close = df_slice['Close'].iloc[-1]
                vol = df_slice['Close'].pct_change().rolling(20).std().iloc[-1]
                high_10 = df_slice['High'].rolling(10).max().iloc[-1]
                pb_ratio = ((high_10 - close) / (high_10 + 1e-9)) / (vol + 1e-9)
                recent_surge = df_slice['Close'].pct_change(10).iloc[-1]
                
                if pb_ratio < 0.8 or recent_surge > (vol * 3.5) or vol < 0.003: continue
                
                pb_score = np.exp(-((pb_ratio - 2.5) ** 2) / (2 * 1.5 ** 2))
                cd_score = np.clip((-recent_surge / (vol + 1e-9)) / 1.5, 0, 1)
                final_score = ((pb_score * 0.7) + (cd_score * 0.3)) * regime_boost
                
                if final_score >= 0.72 and df_slice['Close'].pct_change(1).iloc[-1] > 0:
                    candidates.append({"ticker": ticker, "price": close, "score": final_score, "pb_ratio": pb_ratio, "atr": (df_slice['High'] - df_slice['Low']).rolling(20).mean().iloc[-1]})
            except: continue
        
        candidates = sorted(candidates, key=lambda x: x['score'], reverse=True)
        for cand in candidates[:(5 - len(self.positions))]:
            self.positions.append({"ticker": cand["ticker"], "entry_price": cand["price"], "entry_ts": ts, "entry_atr": cand["atr"], "highest_price": cand["price"], "pb_ratio": cand["pb_ratio"]})

    def _update_and_check_exits(self, data, idx, ts):
        active_positions = []
        for pos in self.positions:
            ticker = pos["ticker"]; curr_price = data[ticker]['Close'].iloc[idx]
            if np.isnan(curr_price): active_positions.append(pos); continue
            if curr_price > pos["highest_price"]: pos["highest_price"] = curr_price
            profit = (curr_price / pos["entry_price"]) - 1
            trail_k = self.base_trail_k * np.clip(pos["pb_ratio"] / 3.0, 0.5, 1.5) * np.clip(profit / 0.02, 0.8, 2.0)
            if curr_price <= pos["entry_price"] - (pos["entry_atr"] * self.sl_k) or (curr_price <= pos["highest_price"] - (pos["entry_atr"] * trail_k) and pos["highest_price"] > pos["entry_price"]) or (ts - pos["entry_ts"]).total_seconds() / 60 >= self.max_mins:
                self.trade_history.append({"pnl": (curr_price / pos["entry_price"]) - 1 - self.cost_ratio})
            else: active_positions.append(pos)
        self.positions = active_positions

    def _analyze(self):
        if not self.trade_history: return
        df = pd.DataFrame(self.trade_history)
        pf = df[df['pnl']>0]['pnl'].sum() / (abs(df[df['pnl']<=0]['pnl'].sum()) + 1e-9)
        print(f"\n--- Physical Baseline OS ---")
        print(f"Total Trades: {len(df)} | Win Rate: {(df['pnl']>0).mean()*100:.2f}% | PF: {pf:.4f}")

if __name__ == "__main__":
    tester = PhysicalPredatorOS(TICKER_LIST)
    tester.run()
