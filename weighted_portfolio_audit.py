import pandas as pd
import numpy as np
import yfinance as yf

# --- Sniper AI V84.0: Weighted Portfolio Audit ---
# 役割: スコアを「ポジションサイズ」として扱い、ロット調整による期待値の増幅を検証する。
# 目的: 情報を捨てずに、エッジの強い場面に資金を集中させるプロの運用モデルをシミュレーションする。

class WeightedAuditor:
    def __init__(self, tickers):
        self.tickers = tickers
        self.trade_records = []

    def run_audit(self, years=1):
        print(f"[*] Auditing Weighted Portfolio Performance over {years} year(s)...")
        data = yf.download(self.tickers, period=f"{years}y", interval="60m", group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        for ticker in self.tickers:
            df = data[ticker].dropna()
            if len(df) < 100: continue
            
            df['sma20'] = df['Close'].rolling(20).mean()
            df['sma50'] = df['Close'].rolling(50).mean()
            
            for i in range(50, len(df)-20):
                # 衝撃 + 沈黙 + 枯渇 (ベース条件)
                if df['sma20'].iloc[i] > df['sma50'].iloc[i] and df['Low'].iloc[i] < (df['sma20'].iloc[i] * 1.01):
                    if i >= 3 and df['Low'].iloc[i-2:i+1].min() >= df['Low'].iloc[i-3]:
                        
                        # スコアリング (0.0 - 2.0)
                        comp = (df['High'].iloc[i-2:i+1].max() / df['Low'].iloc[i-2:i+1].min()) - 1
                        s_comp = np.clip((0.02 - comp) / 0.015, 0, 1)
                        rsi = self._rsi(df['Close'].iloc[i-20:i+1])
                        s_rsi = 1.0 - np.clip(abs(rsi - 50) / 20, 0, 1)
                        total_score = s_comp + s_rsi
                        
                        # リターン記録
                        entry_p = df['Open'].iloc[i+1] * 1.001
                        pnl = 0
                        for k in range(i+1, i+25):
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

        self._report_weighted_performance()

    def _rsi(self, series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-9)
        return 100 - (100 / (1 + rs.iloc[-1]))

    def _report_weighted_performance(self):
        df = pd.DataFrame(self.trade_records)
        if df.empty: return
        
        # 1. 標準的な PF (全ロット均等)
        standard_pf = sum([p for p in df['PnL'] if p > 0]) / (abs(sum([p for p in df['PnL'] if p <= 0])) + 1e-9)
        
        # 2. 加重 PF (ロット = スコア)
        df['Weighted_PnL'] = df['PnL'] * df['Score']
        weighted_pf = sum([p for p in df['Weighted_PnL'] if p > 0]) / (abs(sum([p for p in df['Weighted_PnL'] if p <= 0])) + 1e-9)
        
        # 3. 相関係数
        correlation = df['Score'].corr(df['PnL'])
        
        print("\n" + "="*70)
        print("WEIGHTED PORTFOLIO AUDIT REPORT")
        print("="*70)
        print(f"Total Trades      : {len(df)}")
        print(f"Standard PF       : {standard_pf:.4f}")
        print(f"Weighted PF (V1)  : {weighted_pf:.4f}  (Lot size = Score)")
        print(f"Correlation (S:R) : {correlation:.4f}")
        print("-" * 70)
        
        # 加速モデル (Lot = Score^2)
        df['Aggressive_PnL'] = df['PnL'] * (df['Score'] ** 2)
        aggressive_pf = sum([p for p in df['Aggressive_PnL'] if p > 0]) / (abs(sum([p for p in df['Aggressive_PnL'] if p <= 0])) + 1e-9)
        print(f"Weighted PF (V2)  : {aggressive_pf:.4f}  (Lot size = Score^2)")
        
        print("="*70)
        print("Conclusion: Did weighting the alpha increase the final stability?")
        print("="*70)

if __name__ == "__main__":
    from core import TICKER_LIST
    audit = WeightedAuditor(TICKER_LIST)
    audit.run_audit(years=1)
