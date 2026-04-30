import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V62.0: Growth Limit Research ---
# 役割: ボラティリティの高い中小型・値嵩株において、指値(Limit Order)を用いた逆張りを検証する。
# 目的: 1分足の「遅れ」を逆手に取り、最も有利な安値で「待ち伏せ」してAlphaを厚くする。

# ターゲット銘柄 (ボラティリティと流動性のバランスが良い銘柄)
GROWTH_TICKERS = [
    "7011.T", "9101.T", "4385.T", "4475.T", "6098.T", 
    "6501.T", "8058.T", "9104.T", "9107.T", "6723.T"
]

class GrowthLimitHunter:
    def __init__(self, tickers):
        self.tickers = tickers
        self.results = []

    def run_research(self, days=7):
        print(f"[*] Analyzing Limit Order Alpha on high-volatility tickers...")
        interval = "1m"
        data = yf.download(self.tickers, period=f"{days}d", interval=interval, group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        for ticker in self.tickers:
            df = data[ticker]
            if len(df) < 100: continue
            
            # 中小型向け衝撃検知 (ATR 2.5倍 / Vol 5倍に緩和)
            tr = pd.concat([(df['High']-df['Low']), (df['High']-df['Close'].shift(1)).abs()], axis=1).max(axis=1)
            atr = tr.rolling(20).mean()
            vol_avg = df['Volume'].rolling(20).mean()
            
            for i in range(20, len(df)-25):
                # 衝撃
                if (df['Close'].iloc[i] - df['Close'].shift(1).iloc[i]) < -(atr.iloc[i] * 2.5) and df['Volume'].iloc[i] > (vol_avg.iloc[i] * 5.0):
                    
                    low_shock = df['Low'].iloc[i]
                    
                    # --- Step 1: Silence & Exhaustion 確認 (3分間) ---
                    wait_win = df.iloc[i+1:i+4]
                    no_new_low = wait_win['Low'].min() >= low_shock
                    recovery = (wait_win['Close'].iloc[-1] / df['Close'].iloc[i]) - 1
                    
                    if no_new_low and recovery < 0.005: # 中小型なので戻り閾値は少し広めに
                        
                        # --- Step 2: Limit Order (待ち伏せ) ---
                        # 3分待った後、次の5分間で「衝撃の安値(low_shock)」に指値を置く
                        limit_price = low_shock
                        
                        for k in range(i+4, i+9):
                            if k + 10 >= len(df): break
                            
                            # 指値にタッチしたか (安値が指値以下)
                            if df['Low'].iloc[k] <= limit_price:
                                # 約定成功！ (手数料0.05%程度を想定し、スリッページは0とする)
                                entry_p = limit_price
                                exit_p = df['Close'].iloc[k+10]
                                pnl = (exit_p / entry_p) - 1 - 0.0005 # 手数料引き
                                
                                self.results.append(pnl)
                                break
                    i += 20

        self._analyze_results()

    def _analyze_results(self):
        if not self.results: 
            print("[!] No trades triggered. Limit orders were not hit.")
            return
        trades = np.array(self.results)
        pf = sum([p for p in trades if p > 0]) / (abs(sum([p for p in trades if p <= 0])) + 1e-9)
        
        print("\n" + "="*60)
        print("GROWTH LIMIT HUNTER ANALYSIS (V62.0)")
        print("="*60)
        print(f"Total Trades: {len(trades)}")
        print(f"Win Rate: {(trades > 0).mean()*100:.1f}%")
        print(f"Profit Factor: {pf:.4f}")
        print(f"Avg PnL (Limit Entry, after fees): {trades.mean()*100:+.3f}%")
        print("-" * 60)
        print("Conclusion: Does 'Wait and Limit' create a thicker edge?")
        print("="*60)

if __name__ == "__main__":
    hunter = GrowthLimitHunter(GROWTH_TICKERS)
    hunter.run_research(days=7)
