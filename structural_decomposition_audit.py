import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

# --- Sniper AI V113: Structural Decomposition Audit ---
# 役割: 戦略をロジックではなく「市場構造」と「セクター」で分解し、PF 1.085の正体を暴く。
# 目的: エッジが「普遍的」か「局所的」かを見極め、完成への最終的な確証を得る。

class StructuralAuditor:
    def __init__(self, tickers, fee=0.001, slippage=0.001):
        self.tickers = tickers
        self.cost = fee + slippage
        self.index_data = None

    def prepare_index(self):
        """市場全体のレジーム判定用(日経平均)"""
        df = yf.download("^N225", period="2y", interval="60m", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.index = df.index.tz_localize(None) # Naive
        df['sma20'] = df['Close'].rolling(20).mean()
        df['sma50'] = df['Close'].rolling(50).mean()
        self.index_data = df

    def run_decomposition(self):
        print(f"[*] Starting Structural Decomposition (Cost: {self.cost*100:.2f}%)")
        self.prepare_index()
        all_trades = []

        for t in self.tickers:
            try:
                df = yf.download(t, period="1y", interval="60m", progress=False)
                if df.empty or len(df) < 200: 
                    print(f"   [!] Skipping {t}: Insufficient data")
                    continue
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                df.index = df.index.tz_localize(None)
                
                trades = self._simulate(df, t)
                print(f"   [+] {t:8} | Found {len(trades)} trades")
                all_trades.extend(trades)
            except Exception as e:
                print(f"   [ERR] {t}: {e}")

        self._analyze(all_trades)

    def _simulate(self, df, ticker):
        df['sma20'] = df['Close'].rolling(20).mean()
        df['sma50'] = df['Close'].rolling(50).mean()
        trades = []
        in_pos = False
        entry_p = 0
        
        for i in range(50, len(df)-1):
            if not in_pos and df['sma20'].iloc[i] > df['sma50'].iloc[i] and df['Low'].iloc[i-2:i+1].min() >= df['Low'].iloc[i-3]:
                entry_p = df['Open'].iloc[i+1] * (1 + self.cost/2)
                
                # エントリー時の市場レジーム
                time_idx = df.index[i+1]
                idx_row = self.index_data[self.index_data.index <= time_idx].iloc[-1]
                regime = "BULL" if idx_row['sma20'] > idx_row['sma50'] else "BEAR"
                
                in_pos = True
            elif in_pos:
                pnl = (df['Close'].iloc[i] / entry_p) - 1
                if pnl >= 0.03 or df['Close'].iloc[i] < (df['sma20'].iloc[i] * 0.98):
                    trades.append({
                        'ticker': ticker,
                        'pnl': pnl - self.cost/2,
                        'regime': regime
                    })
                    in_pos = False
        return trades

    def _analyze(self, trades):
        df = pd.DataFrame(trades)
        if df.empty: return
        
        print("\n" + "="*60)
        print("STRUCTURAL DECOMPOSITION REPORT")
        print("="*60)
        
        # 1. 市場レジーム別
        print("\n[ Market Regime Split ]")
        regime_pf = df.groupby('regime').apply(lambda x: self._calc_pf(x['pnl']))
        regime_count = df.groupby('regime').size()
        for r in regime_pf.index:
            print(f"   {r:6} | PF: {regime_pf[r]:.3f} | Count: {regime_count[r]}")
            
        # 2. 銘柄特性別 (PF上位 vs 下位)
        print("\n[ Ticker Concentration Check ]")
        ticker_res = df.groupby('ticker').apply(lambda x: self._calc_pf(x['pnl']))
        top_5 = ticker_res.sort_values(ascending=False).head(5)
        print("   Top 5 Tickers (Sovereign Elite):")
        for t, pf in top_5.items():
            print(f"   {t:8} | PF: {pf:.3f}")
            
        # 3. 損益分布の歪み (Skewness)
        print("\n[ Edge Character ]")
        avg_win = df[df['pnl'] > 0]['pnl'].mean() * 100
        avg_loss = abs(df[df['pnl'] <= 0]['pnl'].mean()) * 100
        print(f"   Avg Win : {avg_win:+.2f}%")
        print(f"   Avg Loss: {avg_loss:.2f}%")
        print(f"   Win Rate: {(df['pnl']>0).mean()*100:.1f}%")
        
        print("="*60)

    def _calc_pf(self, pnl_series):
        wins = pnl_series[pnl_series > 0]
        losses = pnl_series[pnl_series <= 0]
        return sum(wins) / (abs(sum(losses)) + 1e-9)

if __name__ == "__main__":
    from core import TICKER_LIST
    auditor = StructuralAuditor(TICKER_LIST)
    auditor.run_decomposition()
