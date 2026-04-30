import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from core import TICKER_LIST

# --- V24.0 Diagnostic: Loss Pattern Analysis ---
# 役割: 負けトレードのエントリー後の価格推移を詳細に分析。
# 目的: 「反発しない押し目」を何分で見切り、何%で切るべきかの根拠を得る。

class LossAnalyzer:
    def __init__(self, tickers):
        self.tickers = tickers
        self.loss_logs = []

    def run(self):
        print(f"[*] Analyzing Loss Patterns in Graveyard Period (60d to 30d ago)...")
        end_date = datetime.now() - timedelta(days=30)
        start_date = datetime.now() - timedelta(days=59)
        data = yf.download(self.tickers, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), interval="5m", group_by='ticker', progress=False)
        
        for ticker in self.tickers:
            df = data[ticker]
            for i in range(50, len(df)-40):
                try:
                    df_slice = df.iloc[i-50:i]
                    close = df_slice['Close'].iloc[-1]
                    vol = df_slice['Close'].pct_change().rolling(20).std().iloc[-1]
                    high_10 = df_slice['High'].rolling(10).max().iloc[-1]
                    pb_ratio = ((high_10 - close) / (high_10 + 1e-9)) / (vol + 1e-9)
                    
                    # 物理条件(V19.8)
                    if pb_ratio >= 0.8:
                        # エントリー後の推移を追跡 (180分 = 36ステップ)
                        future = df.iloc[i:i+36]
                        if future.empty: continue
                        
                        max_pnl = (future['High'].max() / close) - 1
                        min_pnl = (future['Low'].min() / close) - 1
                        final_pnl = (future['Close'].iloc[-1] / close) - 1
                        
                        # 負けトレード(結果的に損切りラインにかかったもの)を記録
                        if min_pnl < -0.01: 
                            # 30分後(6ステップ)の状況を確認
                            pnl_30m = (future['Close'].iloc[min(5, len(future)-1)] / close) - 1
                            self.loss_logs.append({
                                "ticker": ticker, "pnl_30m": pnl_30m, "min_pnl": min_pnl, "max_pnl": max_pnl, "final_pnl": final_pnl
                            })
                except: continue
        
        self._report()

    def _report(self):
        if not self.loss_logs: return
        df = pd.DataFrame(self.loss_logs)
        print("\n" + "="*40)
        print("LOSS PATTERN DIAGNOSTIC REPORT")
        print("="*40)
        print(f"Total Loss Samples: {len(df)}")
        print(f"Average PnL at 30m for Future Losers: {df['pnl_30m'].mean()*100:.2f}%")
        print(f"Ratio of Losers that were NEVER positive in 30m: {(df['pnl_30m'] < 0).mean()*100:.2f}%")
        print("="*40)

if __name__ == "__main__":
    analyzer = LossAnalyzer(TICKER_LIST)
    analyzer.run()
