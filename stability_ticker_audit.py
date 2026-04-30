import pandas as pd
import numpy as np
import yfinance as yf

# --- Sniper AI V94.0: Stability Ticker Audit ---
# 役割: 銘柄別のバックテスト結果を「前半」と「後半」に分割し、安定性を検証する。
# 目的: 特定の時期の幸運を排し、通年で安定して期待値がプラスの「真の精鋭銘柄」を特定する。

class StabilityTickerAudit:
    def __init__(self, tickers):
        self.tickers = tickers
        self.results = []

    def run_audit(self, period="1y"):
        print(f"[*] Auditing Ticker Stability (Split-Half) over {period}...")
        
        for ticker in self.tickers:
            try:
                raw_df = yf.download(ticker, period=period, interval="60m", progress=False)
                if raw_df.empty or len(raw_df) < 150: continue
                
                # MultiIndex対策 & Casing
                df = raw_df.copy()
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df.index = df.index.tz_localize(None)
                
                # 指標
                df['sma20'] = df['Close'].rolling(20).mean()
                df['sma50'] = df['Close'].rolling(50).mean()
                
                # 期間分割
                mid = len(df) // 2
                periods = [("Full", df), ("First", df.iloc[:mid]), ("Second", df.iloc[mid:])]
                
                p_results = {}
                for name, p_df in periods:
                    trades = self._run_strategy(p_df)
                    p_results[name] = self._calc_metrics(trades)
                
                if p_results["Full"]:
                    self.results.append({
                        "Ticker": ticker,
                        "PF_Total": p_results["Full"][0],
                        "PF_First": p_results["First"][0] if p_results["First"] else 0,
                        "PF_Second": p_results["Second"][0] if p_results["Second"] else 0,
                        "Trades": p_results["Full"][3]
                    })
                    print(f"[+] {ticker}: Total PF {p_results['Full'][0]:.2f} (F: {p_results['First'][0]:.2f}, S: {p_results['Second'][0]:.2f})")
                    
            except Exception as e:
                print(f"[!] Error on {ticker}: {e}")

        self._report()

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

    def _calc_metrics(self, trades):
        if not trades: return None
        arr = np.array(trades)
        wins = arr[arr > 0]
        losses = arr[arr <= 0]
        pf = sum(wins) / (abs(sum(losses)) + 1e-9)
        return pf, (arr > 0).mean(), arr.mean(), len(arr)

    def _report(self):
        if not self.results: return
        df = pd.DataFrame(self.results)
        # 合格銘柄 (前後半ともにPF 1.0超え) を優先
        df['Stable'] = (df['PF_First'] > 1.0) & (df['PF_Second'] > 1.0)
        df = df.sort_values(["Stable", "PF_Total"], ascending=False)
        
        print("\n" + "="*90)
        print("STABILITY TICKER AUDIT: THE IMMUTABLE ELITE")
        print("="*90)
        print(df.head(40).to_string(index=False))
        print("-" * 90)
        print("Conclusion: Tickers with 'Stable=True' are your primary sniper targets.")
        print("="*90)

if __name__ == "__main__":
    from core import TICKER_LIST
    audit = StabilityTickerAudit(TICKER_LIST)
    audit.run_audit()
