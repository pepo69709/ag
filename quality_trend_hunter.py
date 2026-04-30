import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V75.0: The Quality Sniper ---
# 役割: 指数(地合い)と相対強度でトレードを厳選し、トレーリングストップで利益を最大化する。
# 目的: 薄いエッジ(PF1.07)を、実戦に耐えうる太いエッジ(PF1.2+)へと昇華させる。

class QualitySniper:
    def __init__(self, tickers):
        self.tickers = tickers
        self.results = []

    def run_backtest(self, years=1):
        print(f"[*] Extracting Quality Alpha over {years} year(s)...")
        # 指数(^N225)と個別銘柄を同時に取得
        all_symbols = self.tickers + ["^N225"]
        data = yf.download(all_symbols, period=f"{years}y", interval="60m", group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        # 指数のトレンド計算
        idx_df = data["^N225"].dropna()
        idx_df['sma20'] = idx_df['Close'].rolling(20).mean()
        idx_df['sma50'] = idx_df['Close'].rolling(50).mean()
        
        for ticker in self.tickers:
            df = data[ticker].dropna()
            if len(df) < 100: continue
            
            df['sma20'] = df['Close'].rolling(20).mean()
            df['sma50'] = df['Close'].rolling(50).mean()
            
            in_position = False
            entry_p = 0
            max_p = 0
            
            for i in range(50, len(df)-1):
                ts = df.index[i]
                if ts not in idx_df.index: continue
                
                # 1. 地合いフィルタ: 日経平均が上昇トレンド
                market_bull = idx_df['sma20'].loc[ts] > idx_df['sma50'].loc[ts]
                
                # 2. 個別トレンド & 押し目 & 枯渇
                stock_bull = df['sma20'].iloc[i] > df['sma50'].iloc[i]
                is_dip = df['Low'].iloc[i] < (df['sma20'].iloc[i] * 1.01)
                exhaustion = i >= 3 and df['Low'].iloc[i-2:i+1].min() >= df['Low'].iloc[i-3]
                
                # 3. 相対強度: 銘柄が日経平均より強い (直近5日の騰落率比較)
                if i > 20:
                    stock_ret = (df['Close'].iloc[i] / df['Close'].iloc[i-20]) - 1
                    market_ret = (idx_df['Close'].loc[ts] / idx_df['Close'].shift(20).loc[ts]) - 1
                    is_strong = stock_ret > market_ret
                else:
                    is_strong = True

                if not in_position and market_bull and stock_bull and is_dip and exhaustion and is_strong:
                    entry_p = df['Open'].iloc[i+1] * 1.001
                    max_p = entry_p
                    in_position = True
                
                elif in_position:
                    max_p = max(max_p, df['High'].iloc[i])
                    current_p = df['Close'].iloc[i]
                    pnl = (current_p / entry_p) - 1
                    
                    # 出口ロジック: トレーリングストップ
                    # 最高値から1.5%下落、または20SMAを明確に割ったらエグジット
                    trail_stop = current_p < (max_p * 0.985)
                    trend_break = current_p < (df['sma20'].iloc[i] * 0.98)
                    
                    if trail_stop or trend_break:
                        self.results.append(pnl - 0.001)
                        in_position = False

        self._analyze_results()

    def _analyze_results(self):
        if not self.results: 
            print("[!] No trades met the high-quality criteria.")
            return
        trades = np.array(self.results)
        win_rate = (trades > 0).mean()
        pf = sum([p for p in trades if p > 0]) / (abs(sum([p for p in trades if p <= 0])) + 1e-9)
        
        print("\n" + "="*60)
        print("QUALITY SNIPER FINAL REPORT (Regime & Strength)")
        print("="*60)
        print(f"Total Trades: {len(trades)}")
        print(f"Win Rate: {win_rate*100:.1f}%")
        print(f"Profit Factor: {pf:.4f}")
        print(f"Avg PnL per Trade: {trades.mean()*100:+.2f}%")
        print("-" * 60)
        print("Conclusion: Did filtering for quality 'thicken' the alpha?")
        print("="*70)

if __name__ == "__main__":
    from core import TICKER_LIST
    sniper = QualitySniper(TICKER_LIST)
    sniper.run_backtest(years=1)
