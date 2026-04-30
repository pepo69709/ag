import pandas as pd
import numpy as np
import yfinance as yf

# --- Sniper AI V79.0: DNA Distribution Visualizer ---
# 役割: 特徴量の「分布」を可視化し、勝ち組と負け組の重なりを暴く。
# 目的: 平均値の差に騙されず、確率的に優位な「ゾーン」を特定し、スコアリングの基礎を作る。

class DNAVisualizer:
    def __init__(self, tickers):
        self.tickers = tickers
        self.raw_stats = []

    def run_analysis(self, years=1):
        print(f"[*] Extracting DNA distribution data over {years} year(s)...")
        data = yf.download(self.tickers, period=f"{years}y", interval="60m", group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        for ticker in self.tickers:
            df = data[ticker].dropna()
            if len(df) < 100: continue
            
            df['sma20'] = df['Close'].rolling(20).mean()
            df['sma50'] = df['Close'].rolling(50).mean()
            df['vol_avg'] = df['Volume'].rolling(50).mean()
            
            in_position = False
            for i in range(50, len(df)-20):
                if df['sma20'].iloc[i] > df['sma50'].iloc[i] and df['Low'].iloc[i] < (df['sma20'].iloc[i] * 1.01):
                    if i >= 3 and df['Low'].iloc[i-2:i+1].min() >= df['Low'].iloc[i-3]:
                        # 特徴量抽出
                        feat_vol_spike = df['Volume'].iloc[i-3] / (df['vol_avg'].iloc[i-3] + 1e-9)
                        feat_comp = (df['High'].iloc[i-2:i+1].max() / df['Low'].iloc[i-2:i+1].min()) - 1
                        feat_rsi = self._rsi(df['Close'].iloc[i-20:i+1])
                        
                        entry_p = df['Open'].iloc[i+1] * 1.001
                        # 決済結果を取得 (15時間保持または20SMA割れ)
                        exit_p = df['Close'].iloc[i+15] if i+15 < len(df) else df['Close'].iloc[-1]
                        pnl = (exit_p / entry_p) - 1 - 0.001
                        
                        self.raw_stats.append({
                            "PnL": pnl,
                            "Vol_Spike": feat_vol_spike,
                            "Compression": feat_comp,
                            "RSI": feat_rsi
                        })
                        i += 20 # トレード間隔

        self._plot_histograms()

    def _rsi(self, series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-9)
        return 100 - (100 / (1 + rs.iloc[-1]))

    def _plot_histograms(self):
        df = pd.DataFrame(self.raw_stats)
        if df.empty: return
        
        winners = df[df['PnL'] > 0.01]
        losers = df[df['PnL'] <= 0]
        
        print("\n" + "="*80)
        print("DNA DISTRIBUTION REPORT: WINNERS vs LOSERS (Normalized Bins)")
        print("="*80)
        
        for feat in ["RSI", "Compression", "Vol_Spike"]:
            print(f"\n[ Feature: {feat} ]")
            # 10分割のビンを作成
            min_val, max_val = df[feat].min(), df[feat].max()
            if feat == "Compression": max_val = 0.05 # 外れ値カット
            if feat == "Vol_Spike": max_val = 5.0
            
            bins = np.linspace(min_val, max_val, 11)
            w_hist, _ = np.histogram(winners[feat], bins=bins)
            l_hist, _ = np.histogram(losers[feat], bins=bins)
            
            # 正規化 (頻度表示)
            w_norm = (w_hist / (sum(w_hist) + 1e-9)) * 100
            l_norm = (l_hist / (sum(l_hist) + 1e-9)) * 100
            
            print(f"{'Bin Range':20} | {'Winners (%)':12} | {'Losers (%)':12} | {'Edge'}")
            print("-" * 65)
            for j in range(len(w_norm)):
                edge = "WIN+" if w_norm[j] > l_norm[j] + 2 else ("LOSS-" if l_norm[j] > w_norm[j] + 2 else ".")
                print(f"{bins[j]:8.4f} - {bins[j+1]:8.4f} | {w_norm[j]:11.1f}% | {l_norm[j]:11.1f}% | {edge}")
        print("="*80)

if __name__ == "__main__":
    from core import TICKER_LIST
    vis = DNAVisualizer(TICKER_LIST)
    vis.run_analysis(years=1)
