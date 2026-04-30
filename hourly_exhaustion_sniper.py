import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V72.0: Hourly Exhaustion Sniper ---
# 役割: 1時間足のみを使用し、上昇トレンド中の「3時間の沈黙(安値更新停止)」を狙い撃つ。
# 目的: 短期ノイズを完全に排し、ユーザー様のイメージである「ゆったりとした大型株のトレンドフォロー」を完成させる。

class HourlyExhaustionSniper:
    def __init__(self, tickers):
        self.tickers = tickers
        self.results = []

    def run_backtest(self, years=1):
        print(f"[*] Analyzing Hourly Exhaustion over {years} year(s)...")
        # 1時間足で1年分取得 (制約なし)
        data = yf.download(self.tickers, period=f"{years}y", interval="60m", group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        for ticker in self.tickers:
            df = data[ticker].dropna()
            if len(df) < 100: continue
            
            # 指標計算 (1時間足)
            df['sma20'] = df['Close'].rolling(20).mean()
            df['sma50'] = df['Close'].rolling(50).mean()
            
            in_position = False
            entry_p = 0
            
            for i in range(50, len(df)-20):
                # 1. 環境認識: 上昇トレンド (20SMA > 50SMA)
                trend_ok = df['sma20'].iloc[i] > df['sma50'].iloc[i]
                
                # 2. 押し目: 価格が20SMA近傍まで調整
                is_dip = df['Low'].iloc[i] < (df['sma20'].iloc[i] * 1.01)
                
                if not in_position and trend_ok and is_dip:
                    # 3. 1時間足レベルの枯渇 (3時間連続で安値更新なし)
                    # i-2, i-1, i の安値がいずれも i-3 の安値を下回っていない
                    if i < 3: continue
                    exhaustion = df['Low'].iloc[i-2:i+1].min() >= df['Low'].iloc[i-3]
                    
                    if exhaustion:
                        # エントリー (翌時間のOpenで、さらに0.1%滑って買う)
                        entry_p = df['Open'].iloc[i+1] * 1.001
                        in_position = True
                        hold_days = 0
                
                # エグジット: 目標利益 3% または トレンド崩壊(20SMA割れ)
                elif in_position:
                    current_p = df['Close'].iloc[i]
                    pnl = (current_p / entry_p) - 1
                    
                    if pnl >= 0.03: # 3%で悠々と利確
                        self.results.append(pnl - 0.001)
                        in_position = False
                    elif current_p < (df['sma20'].iloc[i] * 0.98): # 損切り (余裕を持たせて2%割り込み)
                        self.results.append(pnl - 0.001)
                        in_position = False

        self._analyze_results()

    def _analyze_results(self):
        if not self.results: 
            print("[!] No trades were triggered. Try adjusting the exhaustion criteria.")
            return
        trades = np.array(self.results)
        win_rate = (trades > 0).mean()
        pf = sum([p for p in trades if p > 0]) / (abs(sum([p for p in trades if p <= 0])) + 1e-9)
        
        print("\n" + "="*60)
        print("HOURLY EXHAUSTION SNIPER REPORT (V72.0 Final)")
        print("="*60)
        print(f"Total Trades: {len(trades)}")
        print(f"Win Rate: {win_rate*100:.1f}%")
        print(f"Profit Factor: {pf:.4f}")
        print(f"Avg PnL per Trade: {trades.mean()*100:+.2f}%")
        print("-" * 60)
        print("Conclusion: Is the '3-Hour Silence' the key to trend recovery?")
        print("="*60)

if __name__ == "__main__":
    from core import TICKER_LIST
    sniper = HourlyExhaustionSniper(TICKER_LIST)
    sniper.run_backtest(years=1)
