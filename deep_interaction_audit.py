import pandas as pd
import numpy as np
import yfinance as yf

# --- Sniper AI V90.0: Deep Interaction Audit ---
# 役割: 4つの新世代特徴量を導入し、それらの「掛け算(Interaction)」による期待値の増幅を検証する。
# 目的: 相関係数 0.10超えを目指し、特定の条件が重なった瞬間にだけ発生する Alpha を特定する。

class DeepInteractionAudit:
    def __init__(self, tickers):
        self.tickers = tickers
        self.records = []

    def run_audit(self, years=1):
        print(f"[*] Extracting Deep Interaction DNA over {years} year(s)...")
        data = yf.download(self.tickers, period=f"{years}y", interval="60m", group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        for ticker in self.tickers:
            df = data[ticker].dropna()
            if len(df) < 150: continue
            
            # --- 1. 指標の構築 ---
            df['sma20'] = df['Close'].rolling(20).mean()
            df['sma50'] = df['Close'].rolling(50).mean()
            
            # ATR
            tr = pd.concat([(df['High']-df['Low']), (df['High']-df['Close'].shift(1)).abs()], axis=1).max(axis=1)
            df['atr'] = tr.rolling(20).mean()
            df['atr_long'] = tr.rolling(100).mean()
            
            for i in range(100, len(df)-25):
                # 基本条件: トレンド中の押し目枯渇
                if df['sma20'].iloc[i] > df['sma50'].iloc[i] and df['Low'].iloc[i] < (df['sma20'].iloc[i] * 1.01):
                    if df['Low'].iloc[i-2:i+1].min() >= df['Low'].iloc[i-3]:
                        
                        # --- 2. 新世代特徴量 (Normalized 0-1) ---
                        # Trend Strength (強いトレンドか)
                        ts = (df['Close'].iloc[i] / df['sma50'].iloc[i]) - 1
                        s_ts = np.clip(ts / 0.05, 0, 1)
                        
                        # Smoothness (なめらかな波か)
                        sm = abs(df['sma20'].iloc[i] - df['sma50'].iloc[i]) / (df['atr'].iloc[i] + 1e-9)
                        s_sm = np.clip(sm / 2.0, 0, 1)
                        
                        # Vol Ratio (相対的な収縮か)
                        vr = df['atr'].iloc[i] / (df['atr_long'].iloc[i] + 1e-9)
                        s_vr = np.clip((1.2 - vr) / 0.7, 0, 1)
                        
                        # Interaction Score (掛け算による増幅)
                        total_score = s_ts * s_vr * s_sm
                        
                        # 3. リターン記録
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

                        self.records.append({"Score": total_score, "PnL": pnl, "TS": s_ts, "SM": s_sm, "VR": s_vr})
                        i += 10

        self._report()

    def _report(self):
        df = pd.DataFrame(self.records)
        if df.empty: return
        
        # 相関
        corr = df['Score'].corr(df['PnL'])
        
        # デシル分析
        df['Decile'] = pd.qcut(df['Score'].rank(method='first'), 10, labels=range(10, 0, -1))
        summary = df.groupby('Decile')['PnL'].agg([
            ('Count', 'count'),
            ('Avg_PnL', lambda x: np.mean(x) * 100),
            ('PF', lambda x: sum([p for p in x if p > 0]) / (abs(sum([p for p in x if p <= 0])) + 1e-9))
        ]).sort_index()

        print("\n" + "="*75)
        print(f"DEEP INTERACTION AUDIT REPORT (Correlation: {corr:.4f})")
        print("="*75)
        print(summary.to_string())
        print("-" * 75)
        print("Analysis: Is the gradient sharper? Target: Decile 1 PF > 1.15")
        print("="*75)

if __name__ == "__main__":
    from core import TICKER_LIST
    audit = DeepInteractionAudit(TICKER_LIST)
    audit.run_audit(years=1)
