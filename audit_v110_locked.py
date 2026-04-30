import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI: Audit V110 LOCKED (Sovereign Implementation) ---
# 仕様書(Evaluation Freeze)との完全一致を保証する最終監査エンジン。
# 修正点: 15トレード未満の銘柄をポートフォリオから物理的に除外。

class LockedAuditor:
    def __init__(self, tickers, fee=0.001, slippage=0.001):
        self.tickers = tickers
        self.total_cost = fee + slippage # 往復 0.2%

    def run_sovereign_exam(self, period="1y"):
        print(f"[*] Starting Sovereign Audit (Strict 15-Trade Filter / Cost: {self.total_cost*100:.2f}%)")
        all_sovereign_trades = []
        ticker_pnls = {}

        for t in self.tickers:
            try:
                df = yf.download(t, period=period, interval="60m", progress=False)
                if len(df) < 200: continue
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                df.index = df.index.tz_localize(None)
                
                trades = self._simulate(df)
                
                # --- [重要] 15トレードの壁 ---
                if len(trades) >= 15:
                    all_sovereign_trades.extend(trades)
                    ticker_pnls[t] = sum([tr['pnl'] for tr in trades])
                    print(f"   [VALID] {t:8} | Trades: {len(trades):3} | PF: {self._calc_pf(trades):.3f}")
                else:
                    if len(trades) > 0:
                        print(f"   [VOID]  {t:8} | Trades: {len(trades):3} (Below 15 - Ignored)")
            except: pass

        self._evaluate(all_sovereign_trades, ticker_pnls)

    def _simulate(self, df):
        df['sma20'] = df['Close'].rolling(20).mean()
        df['sma50'] = df['Close'].rolling(50).mean()
        trades = []
        in_pos = False
        entry_p = 0
        for i in range(50, len(df)-1):
            # 凍結仕様: SMAトレンド + 3時間安値維持
            if not in_pos and df['sma20'].iloc[i] > df['sma50'].iloc[i] and df['Low'].iloc[i-2:i+1].min() >= df['Low'].iloc[i-3]:
                entry_p = df['Open'].iloc[i+1] * (1 + self.total_cost/2) # エントリーコスト
                in_pos = True
            elif in_pos:
                pnl = (df['Close'].iloc[i] / entry_p) - 1
                # 凍結仕様: 3%利確 / 20SMA割れ / 最大-2%損切
                if pnl >= 0.03 or df['Close'].iloc[i] < (df['sma20'].iloc[i] * 0.98) or pnl <= -0.02:
                    trades.append({'time': df.index[i], 'pnl': pnl - self.total_cost/2}) # エグジットコスト
                    in_pos = False
        return trades

    def _calc_pf(self, trades):
        arr = np.array([tr['pnl'] for tr in trades])
        wins = arr[arr > 0]
        losses = arr[arr <= 0]
        return sum(wins) / (abs(sum(losses)) + 1e-9)

    def _evaluate(self, trades_list, ticker_pnls):
        if not trades_list:
            print("\n[!] NO SOVEREIGN TRADES. AUDIT FAILED.")
            return
            
        df_trades = pd.DataFrame(trades_list)
        df_trades['month'] = df_trades['time'].dt.to_period('M')
        
        # 1. 収益性 (Sovereign PF)
        arr = df_trades['pnl'].values
        pf = sum(arr[arr > 0]) / (abs(sum(arr[arr <= 0])) + 1e-9)
        
        # 2. 月別損益
        monthly_pnl = df_trades.groupby('month')['pnl'].sum()
        consecutive_losses = (monthly_pnl < 0).rolling(2).sum().max()
        
        # 3. 銘柄分散度
        positive_pnls = {k: v for k, v in ticker_pnls.items() if v > 0}
        total_pos_pnl = sum(positive_pnls.values())
        max_ticker_share = max(positive_pnls.values()) / total_pos_pnl if total_pos_pnl > 0 else 1

        print("\n" + "="*60)
        print("SOVEREIGN SNIPER AUDIT (FROZEN SPEC COMPLIANT)")
        print("="*60)
        
        checks = [
            ("Sovereign PF >= 1.10", pf >= 1.10, f"Result: {pf:.3f}"),
            ("No 2-Month Loss Streak", consecutive_losses < 2, f"Max Streak: {consecutive_losses}"),
            ("Max Ticker Share < 50%", max_ticker_share < 0.5, f"Max Share: {max_ticker_share*100:.1f}%"),
            ("Total Trades (Valid)", len(df_trades) >= 50, f"Total: {len(df_trades)}")
        ]
        
        all_passed = True
        for name, passed, detail in checks:
            status = "[PASS]" if passed else "[FAIL]"
            if not passed: all_passed = False
            print(f"{status} {name:<25} | {detail}")
            
        print("-" * 60)
        if all_passed:
            print("STATUS: SOVEREIGN COMPLETE. READY FOR DEPLOYMENT.")
        else:
            print("STATUS: REJECTED. SPECIFICATION BREACH DETECTED.")
        print("="*60)

if __name__ == "__main__":
    from core import TICKER_LIST
    auditor = LockedAuditor(TICKER_LIST)
    auditor.run_sovereign_exam()
