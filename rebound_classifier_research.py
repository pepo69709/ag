import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Sniper AI V35.0: Rebound Classifier Research ---
# 役割: 衝撃後の「1分間の挙動」を分析し、反発成功個体(V字)と失敗個体(続落)を分かつ特徴を特定する。
# 目的: 単なるパニック検知を「反発現象の判別」へと進化させる。

class ReboundClassifier:
    def __init__(self, tickers):
        self.tickers = tickers
        self.labeled_events = []

    def run_research(self, days=7):
        print(f"[*] Analyzing 1m micro-behavior after disruption over {days} days...")
        interval = "1m"
        data = yf.download(self.tickers, period=f"{days}d", interval=interval, group_by='ticker', progress=False)
        data.index = data.index.tz_localize(None)
        
        all_dates = data.index.normalize().unique()
        for date in all_dates:
            day_data = data[data.index.normalize() == date]
            for ticker in self.tickers:
                df = day_data[ticker]
                if len(df) < 60: continue
                
                # 衝撃検知 (ATR 3.5倍 / Vol 10倍)
                high_low = df['High'] - df['Low']
                tr = pd.concat([high_low, (df['High'] - df['Close'].shift(1)).abs(), (df['Low'] - df['Close'].shift(1)).abs()], axis=1).max(axis=1)
                atr = tr.rolling(20).mean()
                vol_avg = df['Volume'].rolling(20).mean()
                
                for i in range(20, len(df)-10):
                    curr_move = df['Close'].iloc[i] - df['Close'].shift(1).iloc[i]
                    if abs(curr_move) > (atr.iloc[i] * 3.5) and df['Volume'].iloc[i] > (vol_avg.iloc[i] * 10.0) and curr_move < 0:
                        
                        # --- 特徴量(直後1分間の挙動)の抽出 ---
                        if i + 1 >= len(df): continue
                        
                        # 1. 初動の戻り率 (衝撃の1分後価格 / 衝撃の終値)
                        recovery_1m = (df['Close'].iloc[i+1] / df['Close'].iloc[i]) - 1
                        
                        # 2. 出来高の吸収力 (衝撃直後の出来高 / 衝撃時の出来高)
                        absorption_ratio = df['Volume'].iloc[i+1] / df['Volume'].iloc[i]
                        
                        # 3. 下ヒゲの有無 (1分足のヒゲ)
                        lower_wick = (min(df['Open'].iloc[i+1], df['Close'].iloc[i+1]) - df['Low'].iloc[i+1]) / (df['High'].iloc[i+1] - df['Low'].iloc[i+1] + 1e-9)
                        
                        # --- ラベル設定 (3分後のリターンが +0.3% 以上なら成功) ---
                        # 実戦的に次の足のOpenで入ったと仮定したリターン
                        entry_p = df['Open'].iloc[i+1] * 1.001 
                        exit_p = df['Close'].iloc[i+3] if i+3 < len(df) else df['Close'].iloc[-1]
                        pnl = (exit_p / entry_p) - 1
                        
                        self.labeled_events.append({
                            "ts": df.index[i], "ticker": ticker,
                            "recovery_1m": recovery_1m, 
                            "absorption": absorption_ratio,
                            "wick": lower_wick,
                            "pnl": pnl,
                            "is_success": 1 if pnl > 0.003 else 0
                        })
                        i += 15

        self._report()

    def _report(self):
        if not self.labeled_events: return
        df = pd.DataFrame(self.labeled_events)
        
        print("\n" + "="*70)
        print("REBOUND CLASSIFICATION ANALYSIS")
        print("="*70)
        print(f"Total Events: {len(df)} | Success (PnL > 0.3%): {df['is_success'].sum()}")
        
        # 成功群と失敗群の指標比較
        stats = df.groupby('is_success').agg({
            'recovery_1m': 'mean',
            'absorption': 'mean',
            'wick': 'mean'
        })
        
        print("\nFeature Comparison (Mean):")
        print(stats)
        
        print("-" * 70)
        # 判別条件の仮説テスト
        # 仮説: 初動の戻りがプラス、かつ出来高が一定以上吸い込まれている
        hyp_filter = (df['recovery_1m'] > 0.001) & (df['wick'] > 0.3)
        filtered_df = df[hyp_filter]
        
        if len(filtered_df) > 0:
            filtered_pf = filtered_df[filtered_df['pnl']>0]['pnl'].sum() / (abs(filtered_df[filtered_df['pnl']<=0]['pnl'].sum()) + 1e-9)
            print(f"Filtered Results (Recovery > 0.1% AND Wick > 0.3):")
            print(f"Trades: {len(filtered_df)} | WinRate: {(filtered_df['pnl']>0).mean()*100:.1f}% | PF: {filtered_pf:.4f}")
        else:
            print("No trades met the hypothetical filter.")
        print("="*70)

if __name__ == "__main__":
    from core import TICKER_LIST
    classifier = ReboundClassifier(TICKER_LIST)
    classifier.run_research(days=7)
