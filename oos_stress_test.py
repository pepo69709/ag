import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V58.0: OOS Stress Test ---
# 役割: 未知の銘柄群(OOS)に対し、マイクロブレイク確認と0.2%のスリッページで挑む。
# 目的: 戦略の堅牢性を破壊的な条件下で検証し、真の実力を暴き出す。

# 未知の銘柄群 (OOS Tickers: 異なるセクターから抽出)
OOS_TICKERS = [
    "7203.T", "8306.T", "9984.T", "6758.T", "8316.T", 
    "4063.T", "8035.T", "6954.T", "4519.T", "7741.T",
    "6098.T", "9432.T", "6367.T", "8058.T", "6501.T" # 追加銘柄
]

class OOSStressTest:
    def __init__(self, tickers):
        self.tickers = tickers
        self.results = []

    def run_test(self, days=7): # 1分足のAPI制約に従い7日間に修正
        print(f"[*] Running OOS Stress Test on {len(self.tickers)} unknown tickers...")
        interval = "1m"
        data = yf.download(self.tickers, period=f"{days}d", interval=interval, group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        for ticker in self.tickers:
            df = data[ticker]
            if len(df) < 100: continue
            
            tr = pd.concat([(df['High']-df['Low']), (df['High']-df['Close'].shift(1)).abs()], axis=1).max(axis=1)
            atr = tr.rolling(20).mean()
            vol_avg = df['Volume'].rolling(20).mean()
            
            for i in range(20, len(df)-30):
                # 衝撃
                if (df['Close'].iloc[i] - df['Close'].shift(1).iloc[i]) < -(atr.iloc[i] * 3.5) and df['Volume'].iloc[i] > (vol_avg.iloc[i] * 10.0):
                    
                    # 3分間の沈黙・枯渇確認
                    wait_win = df.iloc[i+1:i+4]
                    recovery = (wait_win['Close'].iloc[-1] / df['Close'].iloc[i]) - 1
                    no_new_low = wait_win['Low'].min() >= df['Low'].iloc[i]
                    vol_decay = wait_win['Volume'].mean() < (df['Volume'].iloc[i] * 0.2)
                    
                    if recovery < 0.001 and no_new_low and vol_decay:
                        # --- V58.0: Micro Break Trigger (直近1分高値超え) ---
                        # 3分待った後の5分間、ブレイクを待つ
                        for k in range(i+4, i+9):
                            if k + 10 >= len(df): break
                            if df['Close'].iloc[k] > df['High'].iloc[k-1]: # マイクロブレイク
                                # 摩擦 0.2% (最悪の約定条件)
                                entry_p = df['Close'].iloc[k] * 1.002
                                exit_p = df['Close'].iloc[k+10]
                                pnl = (exit_p / entry_p) - 1
                                self.results.append(pnl)
                                break
                    i += 25

        self._analyze_results()

    def _analyze_results(self):
        if not self.results: 
            print("[!] No trades triggered in OOS test. Criteria might be too strict.")
            return
        trades = np.array(self.results)
        pf = sum([p for p in trades if p > 0]) / (abs(sum([p for p in trades if p <= 0])) + 1e-9)
        
        print("\n" + "="*60)
        print("OOS STRESS TEST FINAL REPORT")
        print("="*60)
        print(f"Total Trades: {len(trades)}")
        print(f"Win Rate: {(trades > 0).mean()*100:.1f}%")
        print(f"Profit Factor: {pf:.4f}")
        print(f"Avg PnL (After 0.2% Slip): {trades.mean()*100:+.3f}%")
        print("="*60)

if __name__ == "__main__":
    tester = OOSStressTest(OOS_TICKERS)
    tester.run_test(days=7)
