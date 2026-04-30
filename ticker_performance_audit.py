import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

# --- Sniper AI V93.0: Ticker Sniper Audit ---
# 役割: 日経225の全銘柄を個別にバックテストし、銘柄ごとのPFと期待値を算出する。
# 目的: 平均PF 1.07の呪縛を解き、PF 1.3超えの「精鋭銘柄」だけを特定する。

class TickerSniperAudit:
    def __init__(self, tickers):
        self.tickers = tickers
        self.results = []

    def run_audit(self, period="1y"):
        print(f"[*] Starting ticker-by-ticker audit over {period}...")
        
        # バルク取得は避けて1銘柄ずつ確実に
        for ticker in self.tickers:
            try:
                # MultiIndexを回避するために1銘柄ずつ確実に取得
                raw_df = yf.download(ticker, period=period, interval="60m", progress=False)
                if raw_df.empty or len(raw_df) < 150: continue
                
                # カラムの平滑化 (MultiIndex対策)
                df = raw_df.copy()
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                df.index = df.index.tz_localize(None)
                
                # 指標計算
                df['sma20'] = df['Close'].rolling(20).mean()
                df['sma50'] = df['Close'].rolling(50).mean()
                
                trades = []
                in_position = False
                entry_p = 0
                
                for i in range(50, len(df)-20):
                    # 戦略: 3時間枯渇 + トレンド (スカラー値を比較)
                    trend_ok = float(df['sma20'].iloc[i]) > float(df['sma50'].iloc[i])
                    exhaustion = float(df['Low'].iloc[i-2:i+1].min()) >= float(df['Low'].iloc[i-3])
                    
                    if not in_position and trend_ok and exhaustion:
                        entry_p = df['Open'].iloc[i+1] * 1.001
                        in_position = True
                    
                    elif in_position:
                        current_p = df['Close'].iloc[i]
                        pnl_raw = (current_p / entry_p) - 1
                        # 固定エグジット (3% / 2%)
                        if pnl_raw >= 0.03 or current_p < (df['sma20'].iloc[i] * 0.98):
                            trades.append(pnl_raw - 0.001)
                            in_position = False

                if trades:
                    trades_arr = np.array(trades)
                    wins = trades_arr[trades_arr > 0]
                    losses = trades_arr[trades_arr <= 0]
                    
                    pf = sum(wins) / (abs(sum(losses)) + 1e-9)
                    winrate = len(wins) / len(trades_arr)
                    avg_pnl = trades_arr.mean() * 100
                    
                    self.results.append({
                        "Ticker": ticker,
                        "PF": pf,
                        "WinRate": winrate,
                        "AvgPnL": avg_pnl,
                        "Trades": len(trades_arr)
                    })
                    print(f"[+] {ticker}: PF {pf:.2f}, Trades {len(trades_arr)}")
            except Exception as e:
                print(f"[!] Error on {ticker}: {e}")

        self._report()

    def _report(self):
        if not self.results: return
        df = pd.DataFrame(self.results)
        df = df.sort_values("PF", ascending=False)
        
        print("\n" + "="*80)
        print("TICKER SNIPER AUDIT REPORT: THE WINNERS CIRCLE")
        print("="*80)
        print(df.head(30).to_string(index=False)) # 上位30
        print("-" * 80)
        print(f"Top 10 Average PF: {df.head(10)['PF'].mean():.4f}")
        print(f"Overall Average PF: {df['PF'].mean():.4f}")
        print("="*80)
        print("Conclusion: Focus ONLY on tickers with PF > 1.2 and Trades > 15.")
        print("="*80)

if __name__ == "__main__":
    from core import TICKER_LIST
    audit = TickerSniperAudit(TICKER_LIST)
    audit.run_audit()
