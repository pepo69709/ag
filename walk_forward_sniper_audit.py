import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V96.0: Walk-Forward Sniper Audit ---
# 役割: 過去データで銘柄を選定し、未来データで運用する「実戦シミュレーション」を行う。
# 目的: 銘柄選定におけるリーク(未来予知)を排除し、動的ポートフォリオの真の収益力を証明する。

class WalkForwardSniper:
    def __init__(self, tickers):
        self.tickers = tickers
        self.data = {}

    def prepare_data(self, start, end):
        print(f"[*] Fetching historical data for {len(self.tickers)} tickers...")
        for t in self.tickers:
            try:
                df = yf.download(t, start=start, end=end, interval="60m", progress=False)
                if df.empty: continue
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                df.index = df.index.tz_localize(None)
                # 指標
                df['sma20'] = df['Close'].rolling(20).mean()
                df['sma50'] = df['Close'].rolling(50).mean()
                self.data[t] = df
            except: pass

    def run_wfo(self, start_date, total_years=2, train_months=6, test_months=6):
        print(f"[*] Starting Walk-Forward Optimization (Train: {train_months}m / Test: {test_months}m)")
        
        current_start = datetime.strptime(start_date, "%Y-%m-%d")
        all_test_trades = []
        
        while True:
            train_start = current_start
            train_end = train_start + timedelta(days=train_months * 30)
            test_start = train_end
            test_end = test_start + timedelta(days=test_months * 30)
            
            if test_end > datetime.now(): break
            
            print(f"\n[ Window ] Train: {train_start.date()} ~ {train_end.date()} | Test: {test_start.date()} ~ {test_end.date()}")
            
            # --- 1. 銘柄選定 (Training) ---
            pf_rank = {}
            for t, df in self.data.items():
                train_df = df[(df.index >= train_start) & (df.index < train_end)]
                trades = self._run_strategy(train_df)
                pf = self._calc_pf(trades)
                if len(trades) >= 5: # 最低トレード数
                    pf_rank[t] = pf
            
            selected_tickers = sorted(pf_rank, key=pf_rank.get, reverse=True)[:5]
            print(f"  Selected Tickers (Top 5): {selected_tickers}")
            
            # --- 2. 運用 (Testing) ---
            window_test_trades = []
            for t in selected_tickers:
                test_df = self.data[t][(self.data[t].index >= test_start) & (self.data[t].index < test_end)]
                trades = self._run_strategy(test_df)
                window_test_trades.extend(trades)
                all_test_trades.extend(trades)
            
            win_pf = self._calc_pf(window_test_trades)
            print(f"  Window Test PF: {win_pf:.4f} (Trades: {len(window_test_trades)})")
            
            current_start += timedelta(days=test_months * 30)

        self._final_report(all_test_trades)

    def _run_strategy(self, df):
        if len(df) < 50: return []
        trades = []
        in_pos = False
        entry_p = 0
        for i in range(50, len(df)-20):
            trend_ok = float(df['sma20'].iloc[i]) > float(df['sma50'].iloc[i])
            exhaustion = float(df['Low'].iloc[i-2:i+1].min()) >= float(df['Low'].iloc[i-3])
            if not in_pos and trend_ok and exhaustion:
                entry_p = df['Open'].iloc[i+1] * 1.001
                in_pos = True
            elif in_pos:
                pnl = (df['Close'].iloc[i] / entry_p) - 1
                if pnl >= 0.03 or df['Close'].iloc[i] < (df['sma20'].iloc[i] * 0.98):
                    trades.append(pnl - 0.001)
                    in_pos = False
        return trades

    def _calc_pf(self, trades):
        if not trades: return 0
        arr = np.array(trades)
        wins = arr[arr > 0]
        losses = arr[arr <= 0]
        return sum(wins) / (abs(sum(losses)) + 1e-9)

    def _final_report(self, all_trades):
        print("\n" + "="*80)
        print("FINAL WALK-FORWARD PERFORMANCE REPORT (The Real Alpha)")
        print("="*80)
        if not all_trades:
            print("[!] No trades executed in test windows.")
            return
        arr = np.array(all_trades)
        pf = self._calc_pf(all_trades)
        print(f"Total Test Trades : {len(arr)}")
        print(f"Combined Test PF  : {pf:.4f}")
        print(f"Avg PnL per Trade : {arr.mean()*100:+.3f}%")
        print(f"Win Rate          : {(arr > 0).mean()*100:.1f}%")
        print("-" * 80)
        print("Conclusion: If Combined Test PF > 1.15, the dynamic portfolio is viable.")
        print("="*80)

if __name__ == "__main__":
    from core import TICKER_LIST
    sniper = WalkForwardSniper(TICKER_LIST)
    # yfinanceの1時間足制限(730日)に合わせて期間を調整
    start_point = (datetime.now() - timedelta(days=725)).strftime("%Y-%m-%d")
    end_point = datetime.now().strftime("%Y-%m-%d")
    
    sniper.prepare_data(start=start_point, end=end_point)
    # 6ヶ月Training / 3ヶ月Test で回転を速める
    sniper.run_wfo(start_date=start_point, total_years=2, train_months=6, test_months=3)
