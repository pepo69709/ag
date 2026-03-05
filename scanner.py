import yfinance as yf
import pandas as pd
import numpy as np
import requests
import json
import os
from datetime import datetime
import config

# ==========================================
# 🚀 クラウド最適化版：バルク・自動スキャナー
# ==========================================

def calculate_indicators(df_ticker):
    if df_ticker.empty or len(df_ticker) < 25: return None
    try:
        close = pd.to_numeric(df_ticker['Close'], errors='coerce').dropna()
        sma25 = close.rolling(window=25).mean()
        dev = (close / sma25 - 1) * 100
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss.replace(0, 1e-6)).fillna(0)))
        vol_ratio = df_ticker['Volume'] / df_ticker['Volume'].rolling(window=20).mean()
        
        return {
            "price": float(close.iloc[-1]),
            "dev": float(dev.iloc[-1]),
            "rsi": float(rsi.iloc[-1]),
            "vol": float(vol_ratio.iloc[-1]),
            "is_green": bool(close.iloc[-1] > df_ticker['Open'].iloc[-1])
        }
    except: return None

def run_automated_scan():
    print("Fetching market data in bulk...")
    unique_tickers = list(dict.fromkeys(config.WATCH_LIST))
    try:
        full_df = yf.download(" ".join(unique_tickers), period="3mo", interval="1d", group_by='ticker', progress=False)
        
        buys = []
        for ticker in unique_tickers:
            res = calculate_indicators(full_df[ticker])
            if res and res["is_green"]:
                # 黄金条件判定
                if (9.0 <= res["dev"] <= 15.0) and (35 <= res["rsi"] <= 65):
                    buys.append(f"💎 **{ticker}** (乖離:{res['dev']:.1f}% / RSI:{res['rsi']:.1f})")
                elif res["vol"] > 2.0:
                    buys.append(f"📈 **{ticker}** (急騰! 出来高{res['vol']:.1f}倍)")

        # 結果を通知
        if buys:
            msg = "🚀 **【自動パトロール：お宝発見！】**\n\n" + "\n".join(buys)
        else:
            msg = "✅ 自動スキャン完了。現在、黄金条件を満たす銘柄はありません。"
        
        print(msg)
        webhook = os.environ.get("DISCORD_WEBHOOK_URL") or config.DISCORD_WEBHOOK_URL
        if "http" in webhook:
            requests.post(webhook, json={"content": msg})
            
    except Exception as e:
        print(f"Error during scan: {e}")

if __name__ == "__main__":
    run_automated_scan()
