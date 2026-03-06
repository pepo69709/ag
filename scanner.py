import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime, timezone, timedelta
import config

# ==========================================
# 🚨 緊急テスト用：とにかくDiscordを鳴らすためのスキャナー
# ==========================================

JST = timezone(timedelta(hours=9))

def calculate_metrics(df):
    if df.empty or len(df) < 20: return None
    try:
        close = pd.to_numeric(df['Close'], errors='coerce').dropna()
        sma25 = close.rolling(window=25).mean()
        dev = (close / sma25 - 1) * 100
        # テスト用にRSIの計算を簡略化
        rsi = 50.0 
        return {"price": float(close.iloc[-1]), "dev": float(dev.iloc[-1]), "rsi": rsi}
    except: return None

def run_test_scan():
    now_jst = datetime.now(JST)
    # テスト対象を絞る（確実にデータがある主要な銘柄だけ）
    test_tickers = ["7203.T", "6758.T", "9984.T", "8035.T"]
    
    try:
        full_df = yf.download(" ".join(test_tickers), period="1mo", progress=False)
        
        fields = []
        for ticker in test_tickers:
            # 2次元配列の調整（銘柄が複数の場合、yf.downloadの構造が変わるため）
            df_ticker = full_df.xs(ticker, axis=1, level=1) if len(test_tickers) > 1 else full_df
            res = calculate_metrics(df_ticker)
            
            if res:
                # 乖離率がマイナス100%以上（＝ほぼ全ての株が対象）なら通知
                if res["dev"] > -100.0:
                    fields.append({
                        "name": f"✨ テスト検出: {ticker}",
                        "value": f"価格: **{res['price']:,.0f}円**\n乖離: **{res['dev']:+.1f}%**",
                        "inline": True
                    })

        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL") or config.DISCORD_WEBHOOK_URL
        if "http" in webhook_url:
            embed = {
                "title": "🛰️ 【通信テスト：リッチ通知システム】",
                "color": 0x00FF00, # Green for Success
                "description": "これはシステムを新しく書き換えたあとのテスト送信です。\n古いメッセージではなく、このカードが届いていれば成功です！",
                "fields": fields[:10],
                "footer": {"text": f"実行時刻: {now_jst.strftime('%H:%M:%S')}"}
            }
            res = requests.post(webhook_url, json={"embeds": [embed]})
            print(f"Post Status: {res.status_code}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_test_scan()
