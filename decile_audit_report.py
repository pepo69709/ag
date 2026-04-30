import pandas as pd
import numpy as np
import yfinance as yf

# --- Sniper AI V83.0: Decile Audit Report ---
# 役割: 全トレードをスコア順に10等分(デシル)し、期待値の勾配が「なめらか」かを確認する。
# 目的: 上位だけのスパイク(過学習)を暴き、本物のAlphaが存在する「坂道」を見つける。

class DecileAudit:
    def __init__(self, tickers):
        self.tickers = tickers
        self.trade_records = []

    def run_audit(self, years=1):
        print(f"[*] Extracting Decile Data (10% bins) over {years} year(s)...")
        data = yf.download(self.tickers, period=f"{years}y", interval="60m", group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        for ticker in self.tickers:
            df = data[ticker].dropna()
            if len(df) < 100: continue
            
            df['sma20'] = df['Close'].rolling(20).mean()
            df['sma50'] = df['Close'].rolling(50).mean()
            
            for i in range(50, len(df)-20):
                if df['sma20'].iloc[i] > df['sma50'].iloc[i] and df['Low'].iloc[i] < (df['sma20'].iloc[i] * 1.01):
                    if i >= 3 and df['Low'].iloc[i-2:i+1].min() >= df['Low'].iloc[i-3]:
                        
                        # 特徴量
                        comp = (df['High'].iloc[i-2:i+1].max() / df['Low'].iloc[i-2:i+1].min()) - 1
                        s_comp = np.clip((0.02 - comp) / 0.015, 0, 1)
                        rsi = self._rsi(df['Close'].iloc[i-20:i+1])
                        s_rsi = 1.0 - np.clip(abs(rsi - 50) / 20, 0, 1)
                        
                        total_score = s_comp + s_rsi
                        
                        # リターン記録 (1時間足基準のスイング)
                        entry_p = df['Open'].iloc[i+1] * 1.001
                        # 利確3% / 損切 20SMA
                        pnl = 0
                        for k in range(i+1, i+25): # 最大25時間保持
                            if k >= len(df): break
                            curr_p = df['Close'].iloc[k]
                            pnl_raw = (curr_p / entry_p) - 1
                            if pnl_raw >= 0.03:
                                pnl = 0.03 - 0.001
                                break
                            if curr_p < (df['sma20'].iloc[k] * 0.98):
                                pnl = pnl_raw - 0.001
                                break
                            pnl = pnl_raw - 0.001
                        
                        self.trade_records.append({"Score": total_score, "PnL": pnl})
                        i += 10

        self._report_deciles()

    def _rsi(self, series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-9)
        return 100 - (100 / (1 + rs.iloc[-1]))

    def _report_deciles(self):
        df = pd.DataFrame(self.trade_records)
        if df.empty: return
        
        # デシルに分割
        df['Decile'] = pd.qcut(df['Score'], 10, labels=range(10, 0, -1))
        
        summary = df.groupby('Decile')['PnL'].agg([
            ('Count', 'count'),
            ('Avg_PnL', lambda x: np.mean(x) * 100),
            ('WinRate', lambda x: (x > 0).mean() * 100),
            ('PF', lambda x: sum([p for p in x if p > 0]) / (abs(sum([p for p in x if p <= 0])) + 1e-9))
        ]).sort_index()

        print("\n" + "="*75)
        print("DECILE PERFORMANCE REPORT: THE EXPECTANCY GRADIENT")
        print("="*75)
        print(summary.to_string())
        print("-" * 75)
        print("Analysis: Check if Avg_PnL and PF increase smoothly from Decile 10 to 1.")
        print("="*75)

if __name__ == "__main__":
    from core import TICKER_LIST
    audit = DecileAudit(TICKER_LIST)
    audit.run_audit(years=1)
