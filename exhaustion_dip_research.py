import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V71.1: Exhaustion Dip Hunter ---
# 役割: 1時間足の上昇トレンドにおいて、15分足レベルの「枯渇(Exhaustion)」を検知し、押し目の終わりを撃ち抜く。
# 目的: 短期で磨いた枯渇モデルを、大型株の太いトレンドフォローに融合させ、盤石なAlphaを構築する。

class ExhaustionDipHunter:
    def __init__(self, tickers):
        self.tickers = tickers
        self.results = []

    def run_backtest(self, months=2):
        print(f"[*] Fusing Exhaustion Logic with Hourly Trends over {months} months...")
        # 15分足を取得 (トレンドと枯渇の両方をカバー)
        data = yf.download(self.tickers, period=f"{months}mo", interval="15m", group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        for ticker in self.tickers:
            df = data[ticker].dropna()
            if len(df) < 200: continue
            
            # --- 指標計算 ---
            # 1時間足相当のトレンド (15分足×4 = 1時間)
            df['sma20_h'] = df['Close'].rolling(20 * 4).mean()
            df['sma50_h'] = df['Close'].rolling(50 * 4).mean()
            
            in_position = False
            entry_p = 0
            
            for i in range(200, len(df)-15):
                # 1. 環境認識: 1時間足レベルの上昇トレンド
                trend_ok = df['sma20_h'].iloc[i] > df['sma50_h'].iloc[i]
                
                # 2. 押し目の検知: 価格が1時間足20SMA以下、または近傍にいる
                is_dip = df['Low'].iloc[i] < (df['sma20_h'].iloc[i] * 1.005)
                
                if not in_position and trend_ok and is_dip:
                    # 3. 枯渇の確証 (直近4本＝1時間の15分足挙動)
                    # 条件: 15分足で「安値更新が止まった」ことを確認
                    recent_15m = df.iloc[i-3:i+1]
                    exhaustion = recent_15m['Low'].min() >= df['Low'].iloc[i-4] # 前の1時間より安値を更新していない
                    
                    if exhaustion:
                        # エントリー (yfinanceの遅延を想定し、次の足のOpenで0.1%滑って買う)
                        entry_p = df['Open'].iloc[i+1] * 1.001
                        in_position = True
                
                # エグジット: 目標利益 3% または 1時間足20SMAを明確に割ったらカット
                elif in_position:
                    current_p = df['Close'].iloc[i]
                    pnl = (current_p / entry_p) - 1
                    
                    if pnl >= 0.03: # 3%で利確
                        self.results.append(pnl - 0.001)
                        in_position = False
                    elif current_p < (df['sma20_h'].iloc[i] * 0.98): # トレンド崩壊(2%以上の割り込み)
                        self.results.append(pnl - 0.001)
                        in_position = False

        self._analyze_results()

    def _analyze_results(self):
        if not self.results: 
            print("[!] No trades were triggered in the Exhaustion Dip model.")
            return
        trades = np.array(self.results)
        win_rate = (trades > 0).mean()
        pf = sum([p for p in trades if p > 0]) / (abs(sum([p for p in trades if p <= 0])) + 1e-9)
        
        print("\n" + "="*60)
        print("EXHAUSTION DIP HUNTER REPORT (Strategic Master)")
        print("="*60)
        print(f"Total Trades: {len(trades)}")
        print(f"Win Rate: {win_rate*100:.1f}%")
        print(f"Profit Factor: {pf:.4f}")
        print(f"Avg PnL per Trade: {trades.mean()*100:+.2f}%")
        print("-" * 60)
        print("Conclusion: Does 'Exhaustion' fix the dip-buying failure?")
        print("="*60)

if __name__ == "__main__":
    from core import TICKER_LIST
    hunter = ExhaustionDipHunter(TICKER_LIST)
    hunter.run_backtest(months=2)
