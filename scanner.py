import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime, timezone, timedelta
import config

# ==========================================
# 🧠 AI-TRAINER：全自動エントリー・推移記録・勝敗判定システム
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

def update_and_track_progress():
    """過去のシグナル銘柄を追跡し、日々の推移と最終勝敗を記録する"""
    file_path = "trade_tracker.csv"
    if not os.path.exists(file_path): return
    
    # configから目標・損切設定を読み込む
    profit_target = 1 + (config.EXIT_PROFIT_TARGET / 100)
    stop_loss_line = 1 - (config.EXIT_STOP_LOSS / 100)
    
    df = pd.read_csv(file_path)
    pending_mask = df['label'].isna()
    
    for idx, row in df[pending_mask].iterrows():
        ticker = row['ticker']
        entry_p = row['entry_price']
        entry_date = row['timestamp'][:10]
        
        try:
            hist = yf.download(ticker, start=entry_date, progress=False)
            if hist.empty: continue
            
            max_p = hist['High'].max()
            min_p = hist['Low'].min()
            current_p = hist['Close'].iloc[-1]
            current_profit = (current_p / entry_p - 1) * 100
            
            # 推移の記録
            new_log = f"{datetime.now(JST).strftime('%m/%d')}:{current_profit:+.1f}%"
            if pd.isna(df.at[idx, 'progress_path']):
                df.at[idx, 'progress_path'] = new_log
            elif new_log not in str(df.at[idx, 'progress_path']):
                df.at[idx, 'progress_path'] = str(df.at[idx, 'progress_path']) + " | " + new_log

            # 指定された戦略（config）に基づいて自動判定
            if max_p >= entry_p * profit_target:
                df.at[idx, 'label'] = 1
                df.at[idx, 'resolved_date'] = datetime.now(JST).strftime('%Y-%m-%d')
            elif min_p <= entry_p * stop_loss_line:
                df.at[idx, 'label'] = 0
                df.at[idx, 'resolved_date'] = datetime.now(JST).strftime('%Y-%m-%d')
        except: continue
        
    df.to_csv(file_path, index=False, encoding="utf-8-sig")

def run_trainer_scan():
    now_jst = datetime.now(JST)
    unique_tickers = list(dict.fromkeys(config.WATCH_LIST))
    print(f"Trainer Scan Initialized: {now_jst}")
    
    update_and_track_progress()
    
    try:
        full_df = yf.download(" ".join(unique_tickers), period="3mo", interval="1d", group_by='ticker', progress=False)
        
        new_entries = []
        file_path = "trade_tracker.csv"
        
        for ticker in unique_tickers:
            res = calculate_metrics(full_df[ticker])
            if not res: continue
            
            # 黄金条件 (configから動的に取得)
            if (config.ENTRY_DEV_MIN <= res["dev"] <= config.ENTRY_DEV_MAX) and \
               (config.ENTRY_RSI_MIN <= res["rsi"] <= config.ENTRY_RSI_MAX):
                new_entries.append({
                    "timestamp": now_jst.strftime('%Y-%m-%d %H:%M'),
                    "ticker": ticker,
                    "entry_price": res["price"],
                    "feat_dev": res["dev"],
                    "feat_rsi": res["rsi"],
                    "feat_vol": res["vol_ratio"],
                    "progress_path": f"0d:+0.0%",
                    "label": np.nan,
                    "resolved_date": np.nan
                })

        if new_entries:
            new_df = pd.DataFrame(new_entries)
            if os.path.exists(file_path):
                new_df.to_csv(file_path, mode='a', header=False, index=False, encoding="utf-8-sig")
            else:
                new_df.to_csv(file_path, mode='w', header=True, index=False, encoding="utf-8-sig")

        # --- Discord通知 ---
        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL") or config.DISCORD_WEBHOOK_URL
        if "http" in webhook_url:
            fields = []
            for s in new_entries:
                fields.append({
                    "name": f"💎 {s['ticker']}",
                    "value": f"価格: **{s['entry_price']:,.0f}円**\n乖離: **{s['feat_dev']:+.1f}%** / RSI: **{s['feat_rsi']:.1f}**",
                    "inline": True
                })
            
            embed = {
                "title": "🚀 【軍師の知能強化：全自動データ収穫中】",
                "color": 0xDAA520,
                "description": f"解析時刻: {now_jst.strftime('%H:%M')}\n100銘柄のスキャンと、過去銘柄の『推移・勝敗』を自動で記録しました。",
                "fields": fields if fields else [{"name": "状況", "value": "新規シグナルなし。データの蓄積を継続中。"}],
                "footer": {"text": f"目標利益:{config.EXIT_PROFIT_TARGET}% / 損切:{config.EXIT_STOP_LOSS}% で自動判定中"}
            }
            requests.post(webhook_url, json={"embeds": [embed]})

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_trainer_scan()
