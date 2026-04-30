#!/usr/bin/env python
# --------------------------------------------------------------
# compute_future_return.py
# --------------------------------------------------------------
# V14.0: Structural Integrity (Robustness) Edition
#   - Perturbation Test: Varying TOP_N_SLOTS & HORIZONS
#   - Parameter Sensitivity Analysis
#   - Advanced Risk Metrics (Inherited)
# --------------------------------------------------------------

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import timedelta
from tqdm import tqdm
import os
import glob

# ===== 設定 =====
PRIMARY_HORIZONS = [5, 15, 60]
# 堅牢性チェック用の近接ホライズン
CHECK_HORIZONS = [4, 6, 14, 16, 55, 65]
ALL_HORIZONS = sorted(list(set(PRIMARY_HORIZONS + CHECK_HORIZONS)))

INTERVAL = "1m"
TOTAL_COST = 0.003
EXECUTION_JITTER = 0.0005
MIN_VOLUME_USD = 10000

# ===== データ取得 & 処理 (V11-V13継承) =====
def fetch_history(ticker):
    try:
        hist = yf.download(ticker, period="5d", interval=INTERVAL, progress=False, auto_adjust=False)
        if hist.empty: return None
        if hist.index.tz is None:
            hist.index = hist.index.tz_localize("UTC").tz_convert("Asia/Tokyo")
        else:
            hist.index = hist.index.tz_convert("Asia/Tokyo")
        hist.index = hist.index.tz_localize(None)
        if "Volume" in hist.columns:
            vol_usd = (hist["Close"] * hist["Volume"]).mean()
            if vol_usd < MIN_VOLUME_USD: return None
        return hist[["Open", "Close"]]
    except: return None

def get_execution_price(hist, ts):
    idx = hist.index.searchsorted(ts, side="right")
    if idx >= len(hist): return np.nan
    price = hist.iloc[idx]["Open"]
    noise = 1 + np.random.uniform(-EXECUTION_JITTER, EXECUTION_JITTER)
    return price * noise

def compute_returns(df):
    print(f"🚀 Computing returns for horizons: {ALL_HORIZONS}")
    for h in ALL_HORIZONS:
        df[f"future_return_{h}m"] = np.nan

    tickers = df["ticker"].unique()
    for ticker in tqdm(tickers, desc="Tickers"):
        hist = fetch_history(ticker)
        if hist is None: continue
        mask = df["ticker"] == ticker
        for idx, row in df[mask].iterrows():
            ts = pd.to_datetime(row["timestamp"])
            entry_p = get_execution_price(hist, ts)
            if np.isnan(entry_p): continue
            for h in ALL_HORIZONS:
                target = ts + timedelta(minutes=h)
                idx2 = hist.index.searchsorted(target, side="right")
                if idx2 < len(hist):
                    ret = (hist.iloc[idx2]["Close"] - entry_p) / entry_p
                    df.at[idx, f"future_return_{h}m"] = ret - TOTAL_COST
    return df

# ===== 分析エンジン (V14: パラメータ攪乱対応) =====
def run_analysis(df, label, horizon, top_n):
    col = f"future_return_{horizon}m"
    valid = df[["timestamp", "true_ev", col]].dropna().copy()
    if len(valid.groupby("timestamp")) < 30: return None

    # スロット制限 (top_n を可変に)
    top_df = valid.groupby("timestamp").apply(
        lambda x: x.nlargest(min(top_n, len(x)), "true_ev")
    ).reset_index(drop=True)

    def weighted_mean(group):
        w = np.sqrt(np.abs(group["true_ev"]))
        w = w / w.sum() if w.sum() > 0 else np.ones(len(group))/len(group)
        return (group[col] * w).sum()

    portfolio = top_df.groupby("timestamp").apply(weighted_mean).sort_index()
    portfolio.index = pd.to_datetime(portfolio.index)
    daily = portfolio.resample("1D").sum()
    daily = daily[daily != 0]

    if len(daily) < 2: return None

    mean = daily.mean()
    std = daily.std()
    sharpe = (mean / std) * np.sqrt(252) if std > 1e-6 else 0
    cum = (1 + daily).cumprod()
    max_dd = (cum / cum.cummax() - 1).min()

    return {
        "split": label, "horizon": horizon, "top_n": top_n,
        "alpha": mean, "sharpe": sharpe, "max_dd": max_dd
    }

def analyze_robustness(df):
    print("\n" + "="*50)
    print("🧱 SNIPER AI V14.0: STRUCTURAL INTEGRITY TEST")
    print("="*50)
    
    df = df.sort_values("timestamp").reset_index(drop=True)
    results = []
    
    # 拡大ウィンドウの最新期間(OOS_75%)を使用して堅牢性をチェック
    test_start_idx = int(len(df) * 0.75)
    test_df = df.iloc[test_start_idx:].copy()
    
    # 攪乱パラメータセット
    test_slots = [3, 5, 7]
    
    for h in ALL_HORIZONS:
        for n in test_slots:
            label = "Robustness_Test"
            res = run_analysis(test_df, label, h, n)
            if res:
                results.append(res)
    
    return pd.DataFrame(results)

if __name__ == "__main__":
    files = sorted(glob.glob("database_*.csv"))
    db = pd.concat([pd.read_csv(f) for f in files], ignore_index=True) if files else pd.read_csv("database.csv")
    db["timestamp"] = pd.to_datetime(db["timestamp"])
    
    db = compute_returns(db)
    db.to_csv("database_robust.csv", index=False)
    
    robust_report = analyze_robustness(db)
    robust_report.to_csv("robust_report.csv", index=False)
    print("\n[COMPLETE] Structural Integrity report saved to: robust_report.csv")
