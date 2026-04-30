import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V51.0: Loss Pattern Analyzer ---
# 役割: 反発が失敗する（逆張りが負ける）パターンの特徴を抽出し、毒(負け要素)を特定する。
# 目的: 「3分待機」に「価格アクションの確証」と「出来高の拒絶」を加え、精度を実戦級へ引き上げる。

class LossAnalyzer:
    def __init__(self, tickers):
        self.tickers = tickers
        self.trade_data = []

    def run_analysis(self, days=7):
        print(f"[*] Dissecting every failed rebound (Short-lived edges) over {days} days...")
        interval = "1m"
        data = yf.download(self.tickers, period=f"{days}d", interval=interval, group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        all_dates = data.index.normalize().unique()
        for date in all_dates:
            day_data = data[data.index.normalize() == date]
            for ticker in self.tickers:
                df = day_data[ticker]
                if len(df) < 60: continue
                
                # 衝撃 ➡ 圧縮
                tr = pd.concat([(df['High']-df['Low']), (df['High']-df['Close'].shift(1)).abs()], axis=1).max(axis=1)
                atr = tr.rolling(20).mean()
                vol_avg = df['Volume'].rolling(20).mean()
                
                for i in range(20, len(df)-25):
                    if (df['Close'].iloc[i] - df['Close'].shift(1).iloc[i]) < -(atr.iloc[i] * 3.5) and df['Volume'].iloc[i] > (vol_avg.iloc[i] * 10.0):
                        
                        # 圧縮区間の高低
                        range_low = df.iloc[i+1:i+6]['Low'].min()
                        
                        # 下抜け観測 (T+6 〜 T+15)
                        for j in range(i+6, i+16):
                            if df['Low'].iloc[j] < range_low:
                                # --- 3分間の「挙動」を詳細ログ化 ---
                                t_entry = j + 3
                                if t_entry + 10 >= len(df): break
                                
                                # 指標1: 3分間の出来高の推移 (減っているか)
                                vol_during_wait = df['Volume'].iloc[j+1:t_entry+1].mean() / df['Volume'].iloc[j]
                                # 指標2: 3分後の価格位置 (反転の兆し)
                                price_at_t3 = df['Close'].iloc[t_entry]
                                min_price_during_wait = df['Low'].iloc[j:t_entry+1].min()
                                recovery_from_low = (price_at_t3 / min_price_during_wait) - 1
                                
                                # 実際の結果 (逆張りエントリー後 10分PnL)
                                pnl = (df['Close'].iloc[t_entry+10] / price_at_t3) - 1
                                
                                self.trade_data.append({
                                    "ts": df.index[t_entry], "ticker": ticker,
                                    "vol_wait": vol_during_wait,
                                    "rec_from_low": recovery_from_low,
                                    "pnl": pnl, "is_win": 1 if pnl > 0.001 else 0
                                })
                                break
                        i += 25

        self._report()

    def _report(self):
        if not self.trade_data: return
        df = pd.DataFrame(self.trade_data)
        
        print("\n" + "="*70)
        print("LOSS PATTERN ANALYSIS (Silence vs Noise)")
        print("="*70)
        
        # 勝ちトレードと負けトレードの指標比較
        comparison = df.groupby('is_win').agg({
            'vol_wait': 'mean',
            'rec_from_low': 'mean'
        })
        print(comparison)
        
        print("-" * 70)
        losses = df[df['is_win'] == 0]
        wins = df[df['is_win'] == 1]
        print(f"Stats: Wins={len(wins)}, Losses={len(losses)}")
        print(f"Avg Recovery (Wins): {wins['rec_from_low'].mean()*100:.3f}%")
        print(f"Avg Recovery (Losses): {losses['rec_from_low'].mean()*100:.3f}%")
        print("="*70)

if __name__ == "__main__":
    from core import TICKER_LIST
    analyzer = LossAnalyzer(TICKER_LIST)
    analyzer.run_analysis(days=7)
