import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ===========================================================================
# Sniper AI V102: The Precision Sniper (Measurement Overhaul)
# ===========================================================================
# 改修点:
# 1. 堅牢なPF計算: 20トレード未満を排除し、無限大PFを防止。
# 2. NaN対策: データ欠損による判定エラーを厳密に回避。
# 3. Tanh正規化: スコアリングのスケールを統一し、銘柄間の差を吸収。
# ===========================================================================

class PrecisionSniper:
    def __init__(self, tickers):
        self.tickers = tickers

    def calc_robust_pf(self, trades):
        """統計的に信頼できるPFのみを返す"""
        arr = np.array(trades)
        if len(arr) < 15: # 最低サンプル数
            return None
        
        gross_profit = np.sum(arr[arr > 0])
        gross_loss = abs(np.sum(arr[arr < 0]))
        
        if gross_loss == 0:
            return None # 負けゼロは統計的に怪しい
            
        return gross_profit / gross_loss

    def get_precision_score(self, df):
        """Tanh関数による正規化スコア算出"""
        # 最新の指標
        sma20 = df['SMA20'].iloc[-1]
        sma50 = df['SMA50'].iloc[-1]
        if np.isnan(sma20) or np.isnan(sma50): return 0
        
        # 1. トレンド強度 (TS)
        ts_val = (sma20 - sma50) / (sma50 + 1e-9)
        # Tanhで0~1に写像 (50倍は感度調整)
        ts_score = np.tanh(ts_val * 40) 
        
        # 2. 収縮度 (Compression)
        recent = df.tail(20)
        comp_val = (recent['High'].max() - recent['Low'].min()) / (df['Close'].iloc[-1] + 1e-9)
        # 収縮しているほど(値が小さいほど)高スコアに反転
        comp_score = np.tanh((0.05 - comp_val) * 20)
        
        # 最終スコア (0~1)
        score = np.clip((ts_score + comp_score) / 2, 0, 1)
        return score

    def run_audit(self, period="1y"):
        print(f"[*] Starting Precision Audit over {period}...")
        results = []
        
        for t in self.tickers:
            try:
                raw_df = yf.download(t, period=period, interval="60m", progress=False)
                if len(raw_df) < 100: continue
                
                df = raw_df.copy()
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                df.index = df.index.tz_localize(None)
                
                # 指標
                df['SMA20'] = df['Close'].rolling(20).mean()
                df['SMA50'] = df['Close'].rolling(50).mean()
                
                trades = []
                in_pos = False
                entry_p = 0
                
                for i in range(50, len(df)-20):
                    # 安全なデータアクセス
                    s20 = df['SMA20'].iloc[i]
                    s50 = df['SMA50'].iloc[i]
                    if np.isnan(s20) or np.isnan(s50): continue
                    
                    trend_ok = float(s20) > float(s50)
                    exhaustion = float(df['Low'].iloc[i-2:i+1].min()) >= float(df['Low'].iloc[i-3])
                    
                    if not in_pos and trend_ok and exhaustion:
                        entry_p = df['Open'].iloc[i+1] * 1.001
                        in_pos = True
                    elif in_pos:
                        pnl = (df['Close'].iloc[i] / entry_p) - 1
                        if pnl >= 0.03 or df['Close'].iloc[i] < (s20 * 0.98):
                            trades.append(pnl - 0.001)
                            in_pos = False
                
                pf = self.calc_robust_pf(trades)
                if pf:
                    results.append({"Ticker": t, "PF": pf, "Trades": len(trades)})
                    print(f"   {t:8} | PF: {pf:.4f} | Trades: {len(trades)}")
            except Exception as e:
                print(f"   [!] {t} Error: {e}")
                
        self._report(results)

    def _report(self, results):
        df = pd.DataFrame(results)
        if df.empty: return
        print("\n" + "="*60)
        print("PRECISION AUDIT REPORT (The Real Alpha)")
        print("="*60)
        print(df.sort_values("PF", ascending=False).to_string(index=False))
        print("-" * 60)
        print(f"Average Robust PF: {df['PF'].mean():.4f}")
        print("="*60)

if __name__ == "__main__":
    from core import TICKER_LIST
    audit = PrecisionSniper(TICKER_LIST)
    audit.run_audit()
