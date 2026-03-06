import discord
import yfinance as yf
import pandas as pd
import requests
import os
import io
from datetime import datetime, timezone, timedelta
import config

# ==========================================
# 💎 クラウド専用：ハイエンド・レポート・スキャナー
# ==========================================

JST = timezone(timedelta(hours=9))

def calculate_metrics(df):
    if df.empty or len(df) < 50: return None
    close = pd.to_numeric(df['Close'], errors='coerce').dropna()
    sma25 = close.rolling(window=25).mean()
    dev = (close / sma25 - 1) * 100
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi = 100 - (100 / (1 + (gain / loss.replace(0, 1e-6)).fillna(0)))
    return {"price": float(close.iloc[-1]), "dev": float(dev.iloc[-1]), "rsi": float(rsi.iloc[-1])}

def create_embed_field(ticker, res):
    """DiscordのWebhook用の埋め込み辞書を作成"""
    return {
        "name": f"💎 {ticker}",
        "value": f"価格: **{res['price']:,.0f}円**\n乖離: **{res['dev']:+.1f}%** / RSI: **{res['rsi']:.1f}**",
        "inline": True
    }

def run_premium_scan():
    print("Premiun scanning started...")
    unique_tickers = list(dict.fromkeys(config.WATCH_LIST))
    try:
        full_df = yf.download(" ".join(unique_tickers), period="3mo", interval="1d", group_by='ticker', progress=False)
        
        fields = []
        all_results = []
        
        for ticker in unique_tickers:
            res = calculate_metrics(full_df[ticker])
            if not res: continue
            
            # 【黄金条件】
            if (9.0 <= res["dev"] <= 15.0) and (35 <= res["rsi"] <= 65):
                fields.append(create_embed_field(ticker, res))
            
            all_results.append({"銘柄": ticker, "価格": res["price"], "乖離": res["dev"], "RSI": res["rsi"]})

        # Webhookへのリッチな埋め込み通知
        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL") or config.DISCORD_WEBHOOK_URL
        if "http" in webhook_url:
            embed = {
                "title": "🚀 【黄金のモメンタム：自動パトロール】",
                "description": f"解析日時: {datetime.now(JST).strftime('%Y/%m/%d %H:%M')}\n100銘柄をスキャニングしました。",
                "color": 0xDAA520, # Gold
                "fields": fields if fields else [{"name": "状況", "value": "現在、黄金条件に該当する銘柄はありません。守りを固めましょう。"}],
                "footer": {"text": "30分おきに自動監視中。データ抽出: Yahoo Finance API"}
            }
            requests.post(webhook_url, json={"embeds": [embed]})

        # CSV送信 (GitHub Actionsから直接送るにはWebhookのファイル送信が必要ですが、ここではレポートのみ送信)
        print("Scan finished successfully.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_premium_scan()
