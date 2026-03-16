"""
💎 数学増強版データジェネレーター（正直・高精度Ver）
==============================================
統計的異常値(Z-Score)と市場の歪みを数値化し、
「勝てる時だけ戦う」ための特徴量を生成します。
"""

import yfinance as yf
import pandas as pd
import numpy as np
import config
from datetime import datetime, timedelta

def get_val(series, date, default=0.0):
    try:
        d = pd.to_datetime(date).normalize()
        if d in series.index: return float(series.loc[d])
        idx = series.index.get_indexer([d], method='pad')[0]
        return float(series.iloc[idx]) if idx >= 0 else default
    except: return default

def generate_training_data():
    print(f"🚀 【数学強化】AI特訓データの生成を開始します...")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 5)
    training_data = []

    # 日経平均（市場の地合い）
    nikkei = yf.download("^N225", start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False, auto_adjust=True)
    n_close = pd.to_numeric(nikkei['Close'].iloc[:,0] if isinstance(nikkei.columns, pd.MultiIndex) else nikkei['Close'], errors='coerce').dropna()
    n_ret_prev = (n_close.pct_change() * 100).shift(1)
    n_vol_prev = (n_close.pct_change().rolling(20).std() * np.sqrt(252) * 100).shift(1)

    for ticker in config.WATCH_LIST:
        print(f"📈 数学解析中: {ticker}...")
        try:
            hist = yf.download(ticker, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False, auto_adjust=True)
            if len(hist) < 60: continue

            c = pd.to_numeric(hist['Close'].iloc[:,0] if isinstance(hist.columns, pd.MultiIndex) else hist['Close'], errors='coerce')
            o = pd.to_numeric(hist['Open'].iloc[:,0] if isinstance(hist.columns, pd.MultiIndex) else hist['Open'], errors='coerce')
            h = pd.to_numeric(hist['High'].iloc[:,0] if isinstance(hist.columns, pd.MultiIndex) else hist['High'], errors='coerce')
            v = pd.to_numeric(hist['Volume'].iloc[:,0] if isinstance(hist.columns, pd.MultiIndex) else hist['Volume'], errors='coerce')

            # --- 1. 統計的異常値 (Z-Score of price deviation) ---
            sma20 = c.rolling(20).mean()
            std20 = c.rolling(20).std()
            z_score = ((c - sma20) / std20.replace(0, 1e-6)).shift(1) # 昨日時点のZスコア

            # --- 2. ボラティリティ調整済み乖離 ---
            dev = ((c/sma20 - 1) * 100).shift(1)
            atr = (h - c.shift(1)).rolling(14).mean().shift(1) # 変動幅
            dev_adj = (dev / atr.replace(0, 1e-6)).fillna(0)

            # --- 3. 出来高の数学的重み ---
            v_sma = v.rolling(20).mean()
            v_score = (v / v_sma.replace(0, 1e-6)).shift(1)

            # --- 4. RSIの反転力（昨日の変化率） ---
            delta = c.diff()
            gain = delta.where(delta>0, 0).rolling(14).mean()
            loss = (-delta.where(delta<0, 0)).rolling(14).mean()
            rsi = (100 - (100 / (1 + gain/loss.replace(0,1e-6))))
            rsi_diff = (rsi.diff()).shift(1) # RSIが上向き始めたか
            rsi_prev = rsi.shift(1)

            # 窓開け（当日朝に判明）
            gap = (o / c.shift(1) - 1) * 100

            # ターゲット（高値+1%）
            win = (h >= (o * 1.01)).astype(int)

            for i in range(60, len(c)):
                date = c.index[i]
                if pd.isna(z_score.iloc[i]): continue
                
                training_data.append({
                    "timestamp": date.strftime('%Y-%m-%d'),
                    "ticker": ticker,
                    "feat_zscore": round(float(z_score.iloc[i]), 3),       # 数学的異常値
                    "feat_dev_adj": round(float(dev_adj.iloc[i]), 3),    # ボラ調整乖離
                    "feat_vscore": round(float(v_score.iloc[i]), 3),      # 出来高の重み
                    "feat_rsi": round(float(rsi_prev.iloc[i]), 2),
                    "feat_rsi_diff": round(float(rsi_diff.iloc[i]), 2),  # 反転サイン
                    "feat_gap": round(float(gap.iloc[i]), 2),
                    "feat_market_ret": round(get_val(n_ret_prev, date), 2),
                    "feat_market_vol": round(get_val(n_vol_prev, date), 2),
                    "label": int(win.iloc[i])
                })

        except Exception as e: continue

    df = pd.DataFrame(training_data)
    df.to_csv("ai_training_data_math.csv", index=False)
    print(f"✅ 数学強化データ生成完了: {len(df)} 件")

if __name__ == "__main__":
    generate_training_data()
