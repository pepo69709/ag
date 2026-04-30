import pandas as pd
import numpy as np
import yfinance as yf

# --- Sniper AI V95.0: Risk Correlation Audit ---
# 役割: 精鋭銘柄間の相関関係と、非半導体銘柄におけるロジックの汎用性を同時に検証する。
# 目的: セクター依存を排し、リスク分散が効いた「本物のポートフォリオ」の基盤を固める。

class RiskAuditor:
    def __init__(self, elite_tickers, non_semi_tickers):
        self.elite = elite_tickers
        self.non_semi = non_semi_tickers

    def run_audit(self, period="1y"):
        print(f"[*] Auditing Risk & Versatility over {period}...")
        
        # 1. 銘柄間の相関係数チェック (日足リターンベース)
        print("\n[ Step 1: Correlation Matrix (Elite Group) ]")
        price_data = pd.DataFrame()
        for t in self.elite:
            df = yf.download(t, period=period, interval="1d", progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            price_data[t] = df['Close']
        
        corr_matrix = price_data.pct_change().corr()
        print(corr_matrix.round(3))
        
        # 2. 非半導体銘柄でのパフォーマンス検証
        print("\n[ Step 2: Cross-Sector Performance Check ]")
        results = []
        for t in self.non_semi:
            try:
                raw_df = yf.download(t, period=period, interval="60m", progress=False)
                if isinstance(raw_df.columns, pd.MultiIndex): raw_df.columns = raw_df.columns.get_level_values(0)
                df = raw_df.copy()
                df.index = df.index.tz_localize(None)
                
                # 指標
                df['sma20'] = df['Close'].rolling(20).mean()
                df['sma50'] = df['Close'].rolling(50).mean()
                
                trades = self._run_strategy(df)
                pf = self._calc_pf(trades)
                results.append({"Ticker": t, "PF": pf, "Trades": len(trades)})
                print(f"[+] {t:8} | PF: {pf:.4f} | Trades: {len(trades)}")
            except:
                pass
        
        self._final_report(results)

    def _run_strategy(self, df):
        if len(df) < 50: return []
        trades = []
        in_position = False
        entry_p = 0
        for i in range(50, len(df)-20):
            trend_ok = float(df['sma20'].iloc[i]) > float(df['sma50'].iloc[i])
            exhaustion = float(df['Low'].iloc[i-2:i+1].min()) >= float(df['Low'].iloc[i-3])
            if not in_position and trend_ok and exhaustion:
                entry_p = df['Open'].iloc[i+1] * 1.001
                in_position = True
            elif in_position:
                pnl = (df['Close'].iloc[i] / entry_p) - 1
                if pnl >= 0.03 or df['Close'].iloc[i] < (df['sma20'].iloc[i] * 0.98):
                    trades.append(pnl - 0.001)
                    in_position = False
        return trades

    def _calc_pf(self, trades):
        if not trades: return 0
        arr = np.array(trades)
        wins = arr[arr > 0]
        losses = arr[arr <= 0]
        return sum(wins) / (abs(sum(losses)) + 1e-9)

    def _final_report(self, results):
        df = pd.DataFrame(results)
        print("\n" + "="*60)
        print("CROSS-SECTOR ADAPTABILITY REPORT")
        print("="*60)
        print(df.sort_values("PF", ascending=False).to_string(index=False))
        print("-" * 60)
        print(f"Non-Semi Average PF: {df['PF'].mean():.4f}")
        print("="*60)

if __name__ == "__main__":
    ELITE = ["6857.T", "6146.T", "8035.T", "8766.T", "4063.T"]
    NON_SEMI = ["8306.T", "8058.T", "9432.T", "2914.T", "4502.T", "7203.T"]
    audit = RiskAuditor(ELITE, NON_SEMI)
    audit.run_audit()
