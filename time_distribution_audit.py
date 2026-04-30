import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V57.0: Time Distribution Audit ---
# 役割: 待機時間を1分から10分まで連続的に変化させ、期待値の「なめらかさ」を検証する。
# 目的: 特定の数値(3分)への依存を暴き、市場の物理的な需給リセット時間を特定する。

class TimeAudit:
    def __init__(self, tickers):
        self.tickers = tickers

    def run_audit(self, days=7):
        print(f"[*] Auditing wait-time continuity (1m to 10m) over {days} days...")
        interval = "1m"
        data = yf.download(self.tickers, period=f"{days}d", interval=interval, group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        # 待機時間を 1分 から 10分 まで 1分刻みで検証
        wait_times = range(1, 11)
        results = []
        
        for wait_m in wait_times:
            trades = []
            for ticker in self.tickers:
                df = data[ticker]
                if len(df) < 100: continue
                
                tr = pd.concat([(df['High']-df['Low']), (df['High']-df['Close'].shift(1)).abs()], axis=1).max(axis=1)
                atr = tr.rolling(20).mean()
                vol_avg = df['Volume'].rolling(20).mean()
                
                for i in range(20, len(df)-25):
                    # 衝撃検知
                    if (df['Close'].iloc[i] - df['Close'].shift(1).iloc[i]) < -(atr.iloc[i] * 3.5) and df['Volume'].iloc[i] > (vol_avg.iloc[i] * 10.0):
                        
                        # --- 厳密なリアルタイム判定シミュレーション ---
                        # wait_m 分間待機
                        if i + wait_m + 11 >= len(df): continue
                        wait_win = df.iloc[i+1:i+wait_m+1]
                        
                        # 待機期間終了時点(T + wait_m)での情報のみを使用
                        recovery = (wait_win['Close'].iloc[-1] / df['Close'].iloc[i]) - 1
                        no_new_low = wait_win['Low'].min() >= df['Low'].iloc[i]
                        vol_decay = wait_win['Volume'].mean() < (df['Volume'].iloc[i] * 0.2)
                        
                        # 条件合致
                        if recovery < 0.001 and no_new_low and vol_decay:
                            # 待機終了直後のOpenでエントリー (未来リークなし)
                            entry_p = df['Open'].iloc[i+wait_m+1] * 1.001
                            exit_p = df['Close'].iloc[i+wait_m+11]
                            pnl = (exit_p / entry_p) - 1
                            trades.append(pnl)
                        i += 20
            
            if trades:
                avg_pnl = np.mean(trades) * 100
                win_rate = (np.array(trades) > 0).mean() * 100
                results.append({"wait_m": wait_m, "avg_pnl": avg_pnl, "win_rate": win_rate, "count": len(trades)})

        self._report(results)

    def _report(self, results):
        df_res = pd.DataFrame(results)
        print("\n" + "="*70)
        print("WAIT-TIME CONTINUITY REPORT (V57.0 Final Audit)")
        print("="*70)
        print(df_res.to_string(index=False))
        print("-" * 70)
        print("Analysis: Look for a smooth 'Hill' shape, not a single spike.")
        print("="*70)

if __name__ == "__main__":
    from core import TICKER_LIST
    audit = TimeAudit(TICKER_LIST)
    audit.run_audit(days=7)
