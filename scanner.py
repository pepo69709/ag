import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime, timezone, timedelta
import config

# ==========================================
# 🧠 AI-TRAINER：全自動・実況レポート型パトロールシステム (最新版・エラー通知付)
# ==========================================

JST = timezone(timedelta(hours=9))

def calculate_metrics(df):
    if df is None or df.empty or len(df) < 50: return None
    try:
        # yfinanceのデータ形式が異なる場合への対応
        if isinstance(df.columns, pd.MultiIndex):
            close = df['Close'].iloc[:, 0]
            volume = df['Volume'].iloc[:, 0]
        else:
            close = df['Close']
            volume = df['Volume']

        close = pd.to_numeric(close, errors='coerce').dropna()
        sma25 = close.rolling(window=25).mean()
        dev = (close / sma25 - 1) * 100
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss.replace(0, 1e-6)).fillna(0)))
        vol_ratio = volume / volume.rolling(window=20).mean()
        
        return {
            "price": float(close.iloc[-1]),
            "dev": float(dev.iloc[-1]),
            "rsi": float(rsi.iloc[-1]),
            "vol_ratio": float(vol_ratio.iloc[-1])
        }
    except Exception as e:
        print(f"Metrics Error: {e}")
        return None

def update_and_track_progress():
    file_path = "trade_tracker.csv"
    if not os.path.exists(file_path): return
    profit_target = 1 + (config.EXIT_PROFIT_TARGET / 100)
    stop_loss_line = 1 - (config.EXIT_STOP_LOSS / 100)
    try:
        df = pd.read_csv(file_path)
        pending_mask = df['label'].isna()
        for idx, row in df[pending_mask].iterrows():
            ticker = row['ticker']
            entry_p = row['entry_price']
            entry_date = str(row['timestamp'])[:10]
            try:
                hist = yf.download(ticker, start=entry_date, progress=False)
                if hist.empty: continue
                max_p = hist['High'].max()
                min_p = hist['Low'].min()
                current_p = hist['Close'].iloc[-1]
                current_profit = (current_p / entry_p - 1) * 100
                new_log = f"{datetime.now(JST).strftime('%m/%d')}:{current_profit:+.1f}%"
                if pd.isna(df.at[idx, 'progress_path']):
                    df.at[idx, 'progress_path'] = new_log
                elif new_log not in str(df.at[idx, 'progress_path']):
                    df.at[idx, 'progress_path'] = str(df.at[idx, 'progress_path']) + " | " + new_log
                if max_p >= entry_p * profit_target:
                    df.at[idx, 'label'] = 1
                    df.at[idx, 'resolved_date'] = datetime.now(JST).strftime('%Y-%m-%d')
                elif min_p <= entry_p * stop_loss_line:
                    df.at[idx, 'label'] = 0
                    df.at[idx, 'resolved_date'] = datetime.now(JST).strftime('%Y-%m-%d')
            except: continue
        df.to_csv(file_path, index=False, encoding="utf-8-sig")
    except Exception as e:
        print(f"Tracking Error: {e}")

def run_trainer_scan():
    now_jst = datetime.now(JST)
    unique_tickers = list(dict.fromkeys(config.WATCH_LIST))
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL") or config.DISCORD_WEBHOOK_URL
    
    print(f"Scan Initialized: {now_jst}")
    update_and_track_progress()
    
    try:
        # データ取得を安定させるために銘柄を分割してDL
        chunk_size = 50
        all_stats = []
        for i in range(0, len(unique_tickers), chunk_size):
            chunk = unique_tickers[i:i+chunk_size]
            full_df = yf.download(" ".join(chunk), period="3mo", interval="1d", group_by='ticker', progress=False)
            
            for ticker in chunk:
                ticker_df = full_df[ticker] if len(chunk) > 1 else full_df
                res = calculate_metrics(ticker_df)
                if res:
                    all_stats.append({
                        "ticker": ticker, "price": res["price"], "dev": res["dev"], "rsi": res["rsi"], "vol": res["vol_ratio"]
                    })

        # --- 🏆 1. 黄金シグナルの抽出 (AI学習用) ---
        golden_hits = [s for s in all_stats if (config.ENTRY_DEV_MIN <= s["dev"] <= config.ENTRY_DEV_MAX) and (config.ENTRY_RSI_MIN <= s["rsi"] <= config.ENTRY_RSI_MAX)]
        
        # --- 📊 2. 注目TOP 5の抽出 (勢い順) ---
        top_movers = sorted(all_stats, key=lambda x: x['dev'], reverse=True)[:5]

        # CSVに記録
        is_market_day = now_jst.weekday() < 5 # 月〜金
        if golden_hits and is_market_day:
            file_path = "trade_tracker.csv"
            new_entries = []
            for s in golden_hits:
                new_entries.append({
                    "timestamp": now_jst.strftime('%Y-%m-%d %H:%M'),
                    "ticker": s["ticker"], "entry_price": s["price"], "feat_dev": s["dev"], "feat_rsi": s["rsi"], "feat_vol": s["vol"], "progress_path": "0d:+0.0%", "label": np.nan, "resolved_date": np.nan
                })
            new_df = pd.DataFrame(new_entries)
            if os.path.exists(file_path):
                new_df.to_csv(file_path, mode='a', header=False, index=False, encoding="utf-8-sig")
            else:
                new_df.to_csv(file_path, mode='w', header=True, index=False, encoding="utf-8-sig")

        # --- 🚀 Discord通知 ---
        if "http" in webhook_url:
            fields = []
            if golden_hits:
                hits_text = "".join([f"**{s['ticker']}**: {s['price']:,.0f}円 (乖離:{s['dev']:+.1f}%)\n" for s in golden_hits[:5]])
                fields.append({"name": "🔥 【黄金シグナル：即戦力候補】", "value": hits_text, "inline": False})
            
            # 空文字エラーを回避するための文言追加
            movers_text = "".join([f"**{s['ticker']}**: {s['price']:,.0f}円 (乖離:{s['dev']:+.1f}% / RSI:{s['rsi']:.1f})\n" for s in top_movers])
            if movers_text == "":
                movers_text = "銘柄データが取得できませんでした。次回スキャンをお待ちください。"
            
            fields.append({"name": "📊 【本日の注目TOP 5：市場の体温】", "value": movers_text, "inline": False})

            embed = {
                "title": "🛰️ 【全自動AIパトロール：マーケット実況】",
                "color": 0xDAA520 if golden_hits else 0x3498DB,
                "description": f"解析時刻: {now_jst.strftime('%m/%d %H:%M')}\n現在のマーケット状況を報告します。",
                "fields": fields,
                "footer": {"text": f"目標利益:{config.EXIT_PROFIT_TARGET}% / 損切:{config.EXIT_STOP_LOSS}% で監視中"}
            }
            requests.post(webhook_url, json={"embeds": [embed]})

    except Exception as e:
        print(f"Error: {e}")
        # システムエラーをDiscordに通知
        if "http" in webhook_url:
            error_embed = {
                "title": "⚠️ 【BOT警告：システムエラー】",
                "color": 0xFF0000,
                "description": f"プログラム実行中にエラーが発生しました。\nエラー内容: `{str(e)}`",
                "footer": {"text": f"発生時刻: {now_jst.strftime('%H:%M:%S')}"}
            }
            requests.post(webhook_url, json={"embeds": [error_embed]})

if __name__ == "__main__":
    run_trainer_scan()
