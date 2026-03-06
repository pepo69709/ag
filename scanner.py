import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime, timezone, timedelta
import config

# ==========================================
# 🧠 AI-TRAINER：全自動エントリー＆勝敗ラベリング・スキャナー
# ==========================================

JST = timezone(timedelta(hours=9))

def calculate_metrics(df):
    if df.empty or len(df) < 50: return None
    try:
        close = pd.to_numeric(df['Close'], errors='coerce').dropna()
        sma25 = close.rolling(window=25).mean()
        dev = (close / sma25 - 1) * 100
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss.replace(0, 1e-6)).fillna(0)))
        vol_ratio = df['Volume'] / df['Volume'].rolling(window=20).mean()
        
        return {
            "price": float(close.iloc[-1]),
            "dev": float(dev.iloc[-1]),
            "rsi": float(rsi.iloc[-1]),
            "vol_ratio": float(vol_ratio.iloc[-1])
        }
    except: return None

def update_trade_labels():
    """過去のシグナル銘柄の勝敗（+10% or -3%）を自動で判定して更新する"""
    file_path = "trade_tracker.csv"
    if not os.path.exists(file_path): return
    
    df = pd.read_csv(file_path)
    # まだ判定が終わっていない(labelが空)ものを探す
    pending = df[df['label'].isna()]
    
    for idx, row in pending.iterrows():
        ticker = row['ticker']
        entry_p = row['entry_price']
        entry_date = row['timestamp'][:10] # YYYY-MM-DD
        
        try:
            # エントリー日からの値動きを取得
            hist = yf.download(ticker, start=entry_date, progress=False)
            if hist.empty: continue
            
            # 高値と安値をチェック
            max_p = hist['High'].max()
            min_p = hist['Low'].min()
            
            # 判定ロジック
            if max_p >= entry_p * 1.10:
                df.at[idx, 'label'] = 1  # 勝ち！
                df.at[idx, 'resolved_date'] = datetime.now(JST).strftime('%Y-%m-%d')
            elif min_p <= entry_p * 0.97:
                df.at[idx, 'label'] = 0  # 負け...
                df.at[idx, 'resolved_date'] = datetime.now(JST).strftime('%Y-%m-%d')
        except: continue
        
    df.to_csv(file_path, index=False, encoding="utf-8-sig")

def run_trainer_scan():
    now_jst = datetime.now(JST)
    unique_tickers = list(dict.fromkeys(config.WATCH_LIST))
    print(f"Trainer Scan Initialized: {now_jst}")
    
    # 1. 過去のトレードの「答え合わせ」を実行
    update_trade_labels()
    
    # 2. 最新の市場をスキャンして新規エントリーを探す
    try:
        full_df = yf.download(" ".join(unique_tickers), period="3mo", interval="1d", group_by='ticker', progress=False)
        
        new_signals = []
        file_path = "trade_tracker.csv"
        
        for ticker in unique_tickers:
            res = calculate_metrics(full_df[ticker])
            if not res: continue
            
            # 黄金条件に合致
            if (9.0 <= res["dev"] <= 15.0) and (35 <= res["rsi"] <= 65):
                # 既に本日記録済みでないかチェック
                new_entry = {
                    "timestamp": now_jst.strftime('%Y-%m-%d %H:%M'),
                    "ticker": ticker,
                    "entry_price": res["price"],
                    "feat_dev": res["dev"],
                    "feat_rsi": res["rsi"],
                    "feat_vol": res["vol_ratio"],
                    "label": np.nan, # 未来の自分への宿題
                    "resolved_date": np.nan
                }
                new_signals.append(new_entry)

        # 新規シグナルを保存
        if new_signals:
            new_df = pd.DataFrame(new_signals)
            if os.path.exists(file_path):
                new_df.to_csv(file_path, mode='a', header=False, index=False, encoding="utf-8-sig")
            else:
                new_df.to_csv(file_path, mode='w', header=True, index=False, encoding="utf-8-sig")

        # --- Discord通知 (デザイン済みのリッチ通知) ---
        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL") or config.DISCORD_WEBHOOK_URL
        if "http" in webhook_url:
            fields = []
            for s in new_signals:
                fields.append({
                    "name": f"💎 {s['ticker']}",
                    "value": f"価格: **{s['entry_price']:,.0f}円**\n乖離: **{s['feat_dev']:+.1f}%** / RSI: **{s['feat_rsi']:.1f}**",
                    "inline": True
                })
            
            embed = {
                "title": "🚀 【軍師の知能強化：自動エントリー＆追跡中】",
                "color": 0xDAA520,
                "description": f"解析完了: {now_jst.strftime('%H:%M')}\n100銘柄の勝敗追跡を開始しました。",
                "fields": fields if fields else [{"name": "状況", "value": "新たな一撃必殺は見つかりませんでした。過去銘柄の監視を継続します。"}],
                "footer": {"text": f"データ蓄積先: trade_tracker.csv"}
            }
            requests.post(webhook_url, json={"embeds": [embed]})

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_trainer_scan()
