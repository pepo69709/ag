import pandas as pd
import numpy as np
import yfinance as yf

# --- Sniper AI V92.0: Goldilocks Trend Audit ---
# 役割: トレンド強度の「中間層(0.5 rank)」を頂点とする非線形スコアを構築し、期待値を検証する。
# 目的: 強すぎず弱すぎない「黄金の初動」を特定し、PF 1.2超えの安定エッジを抽出する。

class GoldilocksAudit:
    def __init__(self, tickers):
        self.tickers = tickers
        self.raw_data = []

    def run_audit(self, years=1):
        print(f"[*] Analyzing Goldilocks Zone (Centered TS) over {years} year(s)...")
        data = yf.download(self.tickers, period=f"{years}y", interval="60m", group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        for ticker in self.tickers:
            df = data[ticker].dropna()
            if len(df) < 150: continue
            
            df['sma50'] = df['Close'].rolling(50).mean()
            tr = pd.concat([(df['High']-df['Low']), (df['High']-df['Close'].shift(1)).abs(), (df['Low']-df['Close'].shift(1)).abs()], axis=1).max(axis=1)
            df['atr'] = tr.rolling(20).mean()
            df['atr_long'] = tr.rolling(100).mean()
            
            df['TS'] = (df['Close'] - df['sma50']) / (df['sma50'] + 1e-9)
            df['Comp'] = df['atr'] / (df['atr_long'] + 1e-9)
            
            for i in range(100, len(df)-25):
                # 基本: 3時間枯渇
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
                        if curr_p < (df['sma50'].iloc[k] * 0.98):
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
        
        # --- RANK & CENTERED SCORE ---
        df['TS_rank'] = df['TS'].rank(pct=True)
        df['Comp_rank'] = (1 - df['Comp']).rank(pct=True)
        
        # Centered TS (0.5を1.0、0や1を0にする山なりスコア)
        df['TS_centered'] = 1 - 2 * abs(df['TS_rank'] - 0.5) 
        
        # スコア (掛け算)
        df['Score'] = df['TS_centered'] * df['Comp_rank']
        
        # 相関
        corr = df['Score'].corr(df['PnL'], method='spearman')
        
        # デシル分析 (分散と勝率を追加)
        df['Decile'] = pd.qcut(df['Score'].rank(method='first'), 10, labels=range(10, 0, -1))
        summary = df.groupby('Decile')['PnL'].agg([
            ('Count', 'count'),
            ('Avg_PnL', lambda x: np.mean(x) * 100),
            ('Std_PnL', lambda x: np.std(x) * 100),
            ('WinRate', lambda x: (x > 0).mean() * 100),
            ('PF', lambda x: sum([p for p in x if p > 0]) / (abs(sum([p for p in x if p <= 0])) + 1e-9))
        ]).sort_index()

        print("\n" + "="*85)
        print(f"GOLDILOCKS TREND AUDIT (Spearman Corr: {corr:.4f})")
        print("="*85)
        print(summary.to_string())
        print("-" * 85)
        print("Analysis: Is the Goldilocks zone (Decile 10) producing stable, low-variance alpha?")
        print("="*85)

if __name__ == "__main__":
    from core import TICKER_LIST
    audit = GoldilocksAudit(TICKER_LIST)
    audit.run_audit(years=1)
