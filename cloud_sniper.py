import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime

# GitHub SecretsからURLを取得するように設定
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
TICKERS = ["6857.T", "6146.T", "8035.T", "8058.T", "4063.T", "8306.T", "9432.T", "8411.T", "8802.T", "4503.T"]

def check_logic(ticker):
    try:
        df = yf.download(ticker, period="5d", interval="60m", progress=False)
        if len(df) < 10: return False
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        sma20 = df['Close'].rolling(20).mean().iloc[-1]
        sma50 = df['Close'].rolling(50).mean().iloc[-1]
        exhaustion = df['Low'].iloc[-3:].min() >= df['Low'].iloc[-4]
        return (sma20 > sma50) and exhaustion
    except:
        return False

def notify(ticker):
    msg = f"🎯 **[Cloud Sniper] {ticker}**\n条件合致。狙撃準備。"
    requests.post(DISCORD_WEBHOOK, json={"content": msg})

if __name__ == "__main__":
    if not DISCORD_WEBHOOK:
        print("Error: DISCORD_WEBHOOK is not set.")
        exit(1)
        
    print(f"[*] Cloud Scan Started: {datetime.now()}")
    found_any = False
    for t in TICKERS:
        print(f"   [Scan] Checking {t}...")
        if check_logic(t):
            notify(t)
            found_any = True
    
    # ユーザーへの安心用メッセージ
    status_msg = "✅ **Cloud Sniper: 定期巡回完了**\n現在、狙撃条件に合致する銘柄はありません。監視を継続します。"
    if found_any:
        status_msg = "🎯 **Cloud Sniper: 狙撃シグナルを検知しました！**\n詳細は上記の通知を確認してください。"
    
    requests.post(DISCORD_WEBHOOK, json={"content": status_msg})
    print("[*] Scan Finished.")

