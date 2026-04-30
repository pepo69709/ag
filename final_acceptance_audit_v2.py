import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI: Final Acceptance Audit V2 ---
# 改修: 銘柄分散度の計算ロジックを厳密化し、絵文字エラーを排除。

class AcceptanceAuditor:
    def __init__(self, tickers, fee=0.001, slippage=0.001):
        self.tickers = tickers
        self.total_cost = fee + slippage

    def run_final_exam(self, period="1y"):
        print(f"[*] Starting Final Acceptance Audit V2 (Target PF: 1.10)")
        all_trades = []
        ticker_pnls = {}

        for t in self.tickers:
            try:
                df = yf.download(t, period=period, interval="60m", progress=False)
                if len(df) < 200: continue
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                df.index = df.index.tz_localize(None)
                
                trades = self._simulate(df)
                if trades:
                    all_trades.extend(trades)
                    # 銘柄ごとの純利益
                    ticker_pnls[t] = sum([tr['pnl'] for tr in trades])
            except: pass

        self._evaluate(all_trades, ticker_pnls)

    def _simulate(self, df):
        df['sma20'] = df['Close'].rolling(20).mean()
        df['sma50'] = df['Close'].rolling(50).mean()
        trades = []
        in_pos = False
        entry_p = 0
        for i in range(50, len(df)-1):
            if not in_pos and df['sma20'].iloc[i] > df['sma50'].iloc[i] and df['Low'].iloc[i-2:i+1].min() >= df['Low'].iloc[i-3]:
                entry_p = df['Open'].iloc[i+1] * (1 + self.total_cost/2)
                in_pos = True
            elif in_pos:
                pnl = (df['Close'].iloc[i] / entry_p) - 1
                if pnl >= 0.03 or df['Close'].iloc[i] < (df['sma20'].iloc[i] * 0.98):
                    trades.append({'time': df.index[i], 'pnl': pnl - self.total_cost/2})
                    in_pos = False
        return trades

    def _evaluate(self, all_trades_raw, ticker_pnls):
        if not all_trades_raw: return
        df_trades = pd.DataFrame(all_trades_raw)
        df_trades['month'] = df_trades['time'].dt.to_period('M')
        
        # 1. 収益性
        arr = df_trades['pnl'].values
        pf = sum(arr[arr > 0]) / (abs(sum(arr[arr <= 0])) + 1e-9)
        
        # 2. 月別損益
        monthly_pnl = df_trades.groupby('month')['pnl'].sum()
        consecutive_losses = (monthly_pnl < 0).rolling(2).sum().max()
        
        # 3. 銘柄分散度 (正の利益を出した銘柄の中での最大シェア)
        positive_pnls = {k: v for k, v in ticker_pnls.items() if v > 0}
        total_pos_pnl = sum(positive_pnls.values())
        max_ticker_share = max(positive_pnls.values()) / total_pos_pnl if total_pos_pnl > 0 else 1
        
        # 4. 取引数
        avg_trades_per_month = len(df_trades) / len(monthly_pnl)

        print("\n" + "="*60)
        print("SNIPER AI: FINAL COMPLETION CHECKLIST V2")
        print("="*60)
        
        checks = [
            ("PF >= 1.10", pf >= 1.10, f"Result: {pf:.3f}"),
            ("No 2-Month Loss Streak", consecutive_losses < 2, f"Max Streak: {consecutive_losses}"),
            ("Max Ticker Share < 50%", max_ticker_share < 0.5, f"Max Share: {max_ticker_share*100:.1f}%"),
            ("Trades/Month >= 20", avg_trades_per_month >= 20, f"Avg Trades: {avg_trades_per_month:.1f}")
        ]
        
        all_passed = True
        for name, passed, detail in checks:
            status = "[PASS]" if passed else "[FAIL]"
            if not passed: all_passed = False
            print(f"{status} {name:<25} | {detail}")
            
        print("-" * 60)
        if all_passed:
            print("STATUS: COMPLETE. READY FOR DEPLOYMENT.")
        else:
            print("STATUS: INCOMPLETE. DIVERSIFICATION NEEDED.")
        print("="*60)

if __name__ == "__main__":
    from core import TICKER_LIST
    auditor = AcceptanceAuditor(TICKER_LIST)
    auditor.run_final_exam()
