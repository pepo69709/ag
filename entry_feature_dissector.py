import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V77.0: Entry Feature Dissector ---
# 役割: 全1,600回のトレードを「勝ち」と「負け」に分け、エントリー時の特徴量を比較分析する。
# 目的: 平均的なエッジ(PF1.07)を解体し、高勝率・高利益を生む「真のシグナル」の正体を特定する。

class EntryDissector:
    def __init__(self, tickers):
        self.tickers = tickers
        self.trade_data = []

    def run_dissection(self, years=1):
        print(f"[*] Dissecting trade DNA over {years} year(s)...")
        data = yf.download(self.tickers, period=f"{years}y", interval="60m", group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        for ticker in self.tickers:
            df = data[ticker].dropna()
            if len(df) < 100: continue
            
            df['sma20'] = df['Close'].rolling(20).mean()
            df['sma50'] = df['Close'].rolling(50).mean()
            # 出来高平均
            df['vol_avg'] = df['Volume'].rolling(50).mean()
            
            in_position = False
            entry_idx = 0
            
            for i in range(50, len(df)-20):
                trend_ok = df['sma20'].iloc[i] > df['sma50'].iloc[i]
                is_dip = df['Low'].iloc[i] < (df['sma20'].iloc[i] * 1.01)
                
                if not in_position and trend_ok and is_dip:
                    # 3時間の枯渇
                    if i >= 3 and df['Low'].iloc[i-2:i+1].min() >= df['Low'].iloc[i-3]:
                        # --- 特徴量の記録 (エントリーの瞬間のDNA) ---
                        feat_vol_decay = df['Volume'].iloc[i-2:i+1].mean() / (df['Volume'].iloc[i-10:i-3].mean() + 1e-9)
                        feat_vol_spike = df['Volume'].iloc[i-3] / (df['vol_avg'].iloc[i-3] + 1e-9)
                        feat_comp = (df['High'].iloc[i-2:i+1].max() / df['Low'].iloc[i-2:i+1].min()) - 1
                        feat_rsi = self._rsi(df['Close'].iloc[i-20:i+1])
                        
                        entry_idx = i
                        entry_p = df['Open'].iloc[i+1] * 1.001
                        in_position = True
                        
                elif in_position:
                    current_p = df['Close'].iloc[i]
                    pnl = (current_p / entry_p) - 1
                    
                    # 決済 (固定 3% or 20SMA割れ)
                    if pnl >= 0.03 or current_p < (df['sma20'].iloc[i] * 0.98):
                        # 結果をDNAデータとして保存
                        self.trade_data.append({
                            "PnL": pnl - 0.001,
                            "Vol_Decay": feat_vol_decay,
                            "Vol_Spike": feat_vol_spike,
                            "Compression": feat_comp,
                            "RSI": feat_rsi
                        })
                        in_position = False

        self._report_dna()

    def _rsi(self, series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-9)
        return 100 - (100 / (1 + rs.iloc[-1]))

    def _report_dna(self):
        df = pd.DataFrame(self.trade_data)
        if df.empty: return
        
        winners = df[df['PnL'] > 0.01]
        losers = df[df['PnL'] <= 0]
        
        print("\n" + "="*70)
        print("ENTRY DNA ANALYSIS REPORT (Winners vs Losers)")
        print("="*70)
        print(f"Winners (PnL > 1%) count: {len(winners)}")
        print(f"Losers (PnL <= 0) count: {len(losers)}")
        print("-" * 70)
        print("Feature          | Winner Avg | Loser Avg  | Trend")
        print("-" * 70)
        for col in ['Vol_Decay', 'Vol_Spike', 'Compression', 'RSI']:
            w_avg = winners[col].mean()
            l_avg = losers[col].mean()
            diff = "STRICTER" if w_avg < l_avg else "LOOSER"
            print(f"{col:16} | {w_avg:10.4f} | {l_avg:10.4f} | {diff}")
        print("="*70)
        print("Conclusion: Use these DNA signatures to filter out 'Zombie' entries.")
        print("="*70)

if __name__ == "__main__":
    from core import TICKER_LIST
    dissector = EntryDissector(TICKER_LIST)
    dissector.run_dissection(years=1)
