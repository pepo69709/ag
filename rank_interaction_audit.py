import pandas as pd
import numpy as np
import yfinance as yf

# --- Sniper AI V91.0: Rank Interaction Audit ---
# 役割: TS(トレンド強度)とComp(収縮)をランク化し、掛け算による「核となる構造」を抽出する。
# 目的: 相関 0.10超えを目指し、ヒートマップで「真の勝負所」を特定する。

class RankInteractionAudit:
    def __init__(self, tickers):
        self.tickers = tickers
        self.raw_data = []

    def run_audit(self, years=1):
        print(f"[*] Analyzing Rank-based Interaction over {years} year(s)...")
        data = yf.download(self.tickers, period=f"{years}y", interval="60m", group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        for ticker in self.tickers:
            df = data[ticker].dropna()
            if len(df) < 150: continue
            
            # 指標作成
            df['sma50'] = df['Close'].rolling(50).mean()
            tr = pd.concat([(df['High']-df['Low']), (df['High']-df['Close'].shift(1)).abs(), (df['Low']-df['Close'].shift(1)).abs()], axis=1).max(axis=1)
            df['atr'] = tr.rolling(20).mean()
            df['atr_long'] = tr.rolling(100).mean()
            
            # 特徴量
            df['TS'] = (df['Close'] - df['sma50']) / (df['sma50'] + 1e-9)
            df['Comp'] = df['atr'] / (df['atr_long'] + 1e-9)
            
            for i in range(100, len(df)-25):
                # 3時間枯渇 (ベースロジック)
                if df['Low'].iloc[i-2:i+1].min() >= df['Low'].iloc[i-3]:
                    
                    # リターン記録 (3% / 2%)
                    entry_p = df['Open'].iloc[i+1] * 1.001
                    pnl = 0
                    for k in range(i+1, i+25):
                        if k >= len(df): break
                        curr_p = df['Close'].iloc[k]
                        pnl_raw = (curr_p / entry_p) - 1
                        if pnl_raw >= 0.03:
                            pnl = 0.03 - 0.001
                            break
                        if curr_p < (df['sma50'].iloc[k] * 0.98): # SMA50ベースの緩い損切
                            pnl = pnl_raw - 0.001
                            break
                        pnl = pnl_raw - 0.001
                    
                    self.raw_data.append({
                        "TS": df['TS'].iloc[i],
                        "Comp": df['Comp'].iloc[i],
                        "PnL": pnl
                    })
                    i += 10

        self._report()

    def _report(self):
        df = pd.DataFrame(self.raw_data)
        if df.empty: return
        
        # --- RANK 変換 ---
        df['TS_rank'] = df['TS'].rank(pct=True)
        df['Comp_rank'] = (1 - df['Comp']).rank(pct=True) # 小さいほど良いので反転
        
        # スコア (掛け算)
        df['Score'] = df['TS_rank'] * df['Comp_rank']
        
        # 1. 相関 (Spearman)
        corr = df['Score'].corr(df['PnL'], method='spearman')
        
        # 2. デシル分析
        df['Decile'] = pd.qcut(df['Score'].rank(method='first'), 10, labels=range(10, 0, -1))
        decile_summary = df.groupby('Decile')['PnL'].agg([
            ('Count', 'count'),
            ('Avg_PnL', lambda x: np.mean(x) * 100),
            ('PF', lambda x: sum([p for p in x if p > 0]) / (abs(sum([p for p in x if p <= 0])) + 1e-9))
        ]).sort_index()

        # 3. ヒートマップ (テキストベース)
        df['TS_bin'] = pd.qcut(df['TS'], 5, labels=['VL', 'L', 'M', 'H', 'VH'])
        df['Comp_bin'] = pd.qcut(df['Comp'], 5, labels=['VH', 'H', 'M', 'L', 'VL']) # 収縮度
        heatmap = df.pivot_table(values='PnL', index='TS_bin', columns='Comp_bin', aggfunc=lambda x: np.mean(x)*100)

        print("\n" + "="*75)
        print(f"RANK INTERACTION AUDIT (Spearman Corr: {corr:.4f})")
        print("="*75)
        print(decile_summary.to_string())
        print("-" * 75)
        print("HEATMAP (TS vs Compression) - Average PnL %")
        print("-" * 75)
        print(heatmap.round(3).to_string())
        print("-" * 75)
        print("Conclusion: Is there a clear 'Hot Zone' where TS and Comp overlap?")
        print("="*75)

if __name__ == "__main__":
    from core import TICKER_LIST
    audit = RankInteractionAudit(TICKER_LIST)
    audit.run_audit(years=1)
