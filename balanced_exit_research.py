import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V76.0: The Balanced Sniper ---
# 役割: 分割利確(3%)と深いトレーリング(4%幅)を組み合わせ、エッジの「厚み」を物理的に増やす。
# 目的: PF 1.07 のスタートラインを、1.20 以上の「鉄板領域」へと引き上げる。

class BalancedSniper:
    def __init__(self, tickers):
        self.tickers = tickers
        self.results = []

    def run_backtest(self, years=1):
        print(f"[*] Growing the Alpha thickness over {years} year(s)...")
        all_symbols = self.tickers + ["^N225"]
        data = yf.download(all_symbols, period=f"{years}y", interval="60m", group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        # 指数のトレンド計算 (除外用)
        idx_df = data["^N225"].dropna()
        idx_df['sma50'] = idx_df['Close'].rolling(50).mean()
        
        for ticker in self.tickers:
            df = data[ticker].dropna()
            if len(df) < 100: continue
            
            df['sma20'] = df['Close'].rolling(20).mean()
            df['sma50'] = df['Close'].rolling(50).mean()
            
            in_position = False
            entry_p = 0
            max_p_after_half = 0
            half_exited = False
            
            for i in range(50, len(df)-1):
                ts = df.index[i]
                if ts not in idx_df.index: continue
                
                # 1. 除外フィルタ: 日経平均が50SMAより下（完全な下げ相場）ならやらない
                if idx_df['Close'].loc[ts] < idx_df['sma50'].loc[ts]:
                    if not in_position: continue

                # 2. 基本エントリー (トレンド + 押し目 + 3時間枯渇)
                stock_bull = df['sma20'].iloc[i] > df['sma50'].iloc[i]
                is_dip = df['Low'].iloc[i] < (df['sma20'].iloc[i] * 1.01)
                exhaustion = i >= 3 and df['Low'].iloc[i-2:i+1].min() >= df['Low'].iloc[i-3]
                
                if not in_position and stock_bull and is_dip and exhaustion:
                    entry_p = df['Open'].iloc[i+1] * 1.001
                    in_position = True
                    half_exited = False
                    max_p_after_half = entry_p
                
                # 3. 進化したエグジットロジック
                elif in_position:
                    current_p = df['Close'].iloc[i]
                    pnl_raw = (current_p / entry_p) - 1
                    
                    # A. 第1段階: 3%で半分利確
                    if not half_exited and pnl_raw >= 0.03:
                        half_pnl = 0.03 - 0.001
                        half_exited = True
                        max_p_after_half = current_p
                    
                    # B. 第2段階: 残りを深いトレーリング(4%)で追う
                    if half_exited:
                        max_p_after_half = max(max_p_after_half, df['High'].iloc[i])
                        # 最高値から4%下落、または20SMAを2%以上割ったら全決済
                        if current_p < (max_p_after_half * 0.96) or current_p < (df['sma20'].iloc[i] * 0.98):
                            final_pnl = (pnl_raw - 0.001 + half_pnl) / 2 # 平均PnL
                            self.results.append(final_pnl)
                            in_position = False
                    
                    # C. 損切り: 一律 -3% または トレンド崩壊
                    elif pnl_raw <= -0.03 or current_p < (df['sma20'].iloc[i] * 0.98):
                        self.results.append(pnl_raw - 0.001)
                        in_position = False

        self._analyze_results()

    def _analyze_results(self):
        if not self.results: 
            print("[!] No trades met the criteria.")
            return
        trades = np.array(self.results)
        win_rate = (trades > 0).mean()
        pf = sum([p for p in trades if p > 0]) / (abs(sum([p for p in trades if p <= 0])) + 1e-9)
        
        print("\n" + "="*60)
        print("BALANCED SNIPER FINAL REPORT (Split-Exit Model)")
        print("="*60)
        print(f"Total Trades: {len(trades)}")
        print(f"Win Rate: {win_rate*100:.1f}%")
        print(f"Profit Factor: {pf:.4f}")
        print(f"Avg PnL per Trade: {trades.mean()*100:+.3f}%")
        print("-" * 60)
        print("Conclusion: Did Split-Exit 'thicken' the Alpha to the target?")
        print("="*60)

if __name__ == "__main__":
    from core import TICKER_LIST
    sniper = BalancedSniper(TICKER_LIST)
    sniper.run_backtest(years=1)
