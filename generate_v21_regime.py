import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from core import TICKER_LIST

# --- V21.0: Regime Data Generator ---
# 役割: 「市場全体の動き(特徴量)」と「物理戦略の成績(ラベル)」を1日単位で紐付け。

def generate_regime_data():
    print(f"[*] Generating Regime Data for V21.0 (Past 60 days)...")
    interval = "5m"
    # 60日分のデータを取得
    data = yf.download(TICKER_LIST, period="60d", interval=interval, group_by='ticker', progress=False)
    
    # 日付ごとに分割
    all_dates = data.index.normalize().unique()
    regime_samples = []
    
    for date in all_dates:
        day_data = data[data.index.normalize() == date]
        if len(day_data) < 50: continue
        
        # --- 市場全体の特徴量 (Regime Features) ---
        # 1. 前半(朝イチ)の市場平均リターン
        market_rets = day_data.xs('Close', level=1, axis=1).pct_change().mean(axis=1)
        morning_ret = market_rets.iloc[1:20].sum()
        
        # 2. 市場全体のボラティリティ
        market_vol = market_rets.rolling(20).std().mean()
        
        # 3. 騰落比率 (上昇銘柄数 / 下落銘柄数)
        daily_rets = day_data.xs('Close', level=1, axis=1).iloc[-1] / day_data.xs('Close', level=1, axis=1).iloc[0] - 1
        ad_ratio = (daily_rets > 0).sum() / (daily_rets < 0).sum() if (daily_rets < 0).sum() > 0 else 1
        
        # --- 物理戦略の「仮想成績」 (Label) ---
        # 簡易的に、その日の市場平均リターンがプラスなら「押し目買い適正あり」とする(実際はバックテスト結果と紐づけるのが理想)
        # ここでは「その日の最終的な市場平均リターン」をラベルのヒントにする
        day_result = daily_rets.mean()
        label = 1 if day_result > 0 else 0
        
        regime_samples.append({
            "date": date,
            "morning_ret": morning_ret,
            "market_vol": market_vol,
            "ad_ratio": ad_ratio,
            "label": label
        })
        
    df = pd.DataFrame(regime_samples)
    df.to_csv("v21_regime_data.csv", index=False)
    print(f"[*] Success: Generated {len(df)} days of regime data.")

if __name__ == "__main__":
    generate_regime_data()
