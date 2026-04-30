import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V70.0: Strategic Trend Hunter ---
# 役割: 大型株において「1時間足」レベルの太い上昇トレンドを捉え、数%の利益を狙う。
# 目的: yfinanceの遅延を考慮しつつ、ゆったりとしたトレンドフォローで着実に利益を出す。

class StrategicTrendHunter:
    def __init__(self, tickers):
        self.tickers = tickers
        self.results = []

    def run_backtest(self, months=3):
        print(f"[*] Analyzing hourly trends on large-cap tickers over {months} months...")
        # 1時間足で過去3ヶ月分を取得
        data = yf.download(self.tickers, period=f"{months}mo", interval="60m", group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        for ticker in self.tickers:
            df = data[ticker].dropna()
            if len(df) < 100: continue
            
            # --- 指標: トレンドの定義 (20時間線と50時間線) ---
            df['sma20'] = df['Close'].rolling(20).mean()
            df['sma50'] = df['Close'].rolling(50).mean()
            
            # ボラティリティ (ATR)
            high_low = df['High'] - df['Low']
            tr = pd.concat([high_low, (df['High'] - df['Close'].shift(1)).abs(), (df['Low'] - df['Close'].shift(1)).abs()], axis=1).max(axis=1)
            atr = tr.rolling(20).mean()

            in_position = False
            entry_p = 0
            
            for i in range(50, len(df)-1):
                # エントリーロジック:
                # 1. 20SMA > 50SMA (上昇トレンドの基本)
                # 2. 直近3時間の高値を更新 (ブレイクアウト)
                # 3. 20分程度のデータ遅延を考慮しても、まだ「波」の途中である
                if not in_position:
                    if df['Close'].iloc[i] > df['sma20'].iloc[i] > df['sma50'].iloc[i]:
                        recent_high = df['High'].iloc[i-3:i].max()
                        if df['Close'].iloc[i] > recent_high:
                            # エントリー (yfinanceの遅延を考慮し、次の時間のOpenで、さらに0.1%滑って買う)
                            entry_p = df['Open'].iloc[i+1] * 1.001
                            in_position = True
                
                # エグジットロジック: 
                # 1. 目標利益 (2%) 達成
                # 2. あるいは、20SMAを下回ったら損切り
                elif in_position:
                    current_p = df['Close'].iloc[i]
                    pnl = (current_p / entry_p) - 1
                    
                    if pnl >= 0.02: # 2%上がったら売る
                        self.results.append(pnl - 0.001) # 手数料引き
                        in_position = False
                    elif current_p < df['sma20'].iloc[i]: # トレンド崩壊
                        self.results.append(pnl - 0.001)
                        in_position = False

        self._analyze_results()

    def _analyze_results(self):
        if not self.results: 
            print("[!] No trades were triggered in the trend following model.")
            return
        trades = np.array(self.results)
        win_rate = (trades > 0).mean()
        pf = sum([p for p in trades if p > 0]) / (abs(sum([p for p in trades if p <= 0])) + 1e-9)
        
        print("\n" + "="*60)
        print("STRATEGIC TREND HUNTER REPORT (Hourly Master)")
        print("="*60)
        print(f"Total Trades: {len(trades)}")
        print(f"Win Rate: {win_rate*100:.1f}%")
        print(f"Profit Factor: {pf:.4f}")
        print(f"Avg PnL per Trade: {trades.mean()*100:+.2f}%")
        print("-" * 60)
        print("Conclusion: Is a slower, thicker trend more stable?")
        print("="*60)

if __name__ == "__main__":
    from core import TICKER_LIST
    hunter = StrategicTrendHunter(TICKER_LIST)
    hunter.run_backtest(months=3)
