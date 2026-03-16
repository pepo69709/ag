"""
🔫 スナイパー・パトロール (数学モデル・クラウド実戦版)
==============================================
1. 朝 8:55: 数学的に激熱な銘柄をスキャニングして通知
2. 9:00〜15:00: スナイパー銘柄を3分おきに監視
3. 達成・撤退をGASダッシュボードへ送信＆通知
"""

import yfinance as yf
import pandas as pd
import numpy as np
import joblib
import time
import requests
import os
from datetime import datetime, timedelta, timezone
import config

# 日本時間(JST)の設定
JST = timezone(timedelta(hours=9), 'JST')

def get_now():
    """常に日本時間を取得"""
    return datetime.now(JST)


# モデルロード
try:
    model = joblib.load('trained_ai_model.pkl')
except:
    model = None

# 通知先の設定（GitHub Secrets または config.py から取得）
DISCORD_URL = os.environ.get("DISCORD_WEBHOOK_URL") or config.DISCORD_WEBHOOK_URL
GAS_URL = os.environ.get("GAS_WEBHOOK_URL") or getattr(config, "GAS_WEBHOOK_URL", "")

def send_notification(msg):
    """Discordへ通知"""
    print(f"📢 Notification: {msg}")
    if not DISCORD_URL: return
    try:
        requests.post(DISCORD_URL, json={"content": msg}, timeout=10)
    except Exception as e:
        print(f"⚠️ Discord通知失敗: {e}")

def send_to_gas(data):
    """GASダッシュボードへ送信"""
    if not GAS_URL: return
    try:
        requests.post(GAS_URL, json=data, timeout=10)
    except Exception as e:
        print(f"⚠️ GAS送信失敗: {e}")

def get_current_data(ticker):
    """現在の価格と高値・安値を取得"""
    try:
        t = yf.Ticker(ticker)
        d = t.history(period="1d")
        if d.empty: return None
        return {
            "open": d['Open'].iloc[0],
            "high": d['High'].iloc[0],
            "low": d['Low'].iloc[0],
            "current": d['Close'].iloc[-1]
        }
    except: return None

def live_patrol():
    """本番：日中の利確・損切監視"""
    # 実際にはここでスキャンしてターゲットを決めるが、
    # 今日はテスト用に「オリンパス(7733.T)」を仮のターゲットにする場合もある
    targets = {
        # "7733.T": {"entry_p": 0.0, "status": "watching"},
    }
    
    print("🕵️ パトロール開始...")
    
    while True:
        now = datetime.now()
        
        # 市場終了(15:01)でリセット
        if now.hour == 15 and now.minute >= 1:
            print("🕒 市場終了。リセット信号を送信します。")
            send_to_gas({"action": "reset"})
            break
            
        # 市場外(15-翌8時)なら待機
        if now.hour > 15 or now.hour < 8:
            print("💤 市場外時間です。")
            break

        # ターゲットの監視
        for ticker, info in targets.items():
            if info["status"] != "watching": continue
            
            data = get_current_data(ticker)
            if not data: continue
            
            if info["entry_p"] == 0:
                info["entry_p"] = data["open"]
                print(f"🚀 {ticker} 寄り付き確定: {data['open']}")
            
            profit_pct = (data["current"] / info["entry_p"] - 1) * 100
            high_pct = (data["high"] / info["entry_p"] - 1) * 100
            low_pct = (data["low"] / info["entry_p"] - 1) * 100
            
            # ダッシュボード更新
            send_to_gas({
                "ticker": ticker,
                "profit": round(profit_pct, 2),
                "status": "active"
            })
            
            if high_pct >= config.EXIT_PROFIT_TARGET:
                msg = f"🏆 【利確】{ticker} 1%達成なのだ！金メダルなのだ！"
                send_notification(msg)
                send_to_gas({"ticker": ticker, "status": "gold"})
                info["status"] = "success"
                
            elif low_pct <= -config.EXIT_STOP_LOSS:
                msg = f"💜 【撤退】{ticker} 損切り。ここは引くのも勇気なのだ。"
                send_notification(msg)
                send_to_gas({"ticker": ticker, "status": "purple"})
                info["status"] = "fail"

        time.sleep(config.SCAN_INTERVAL_MIN * 60)

if __name__ == "__main__":
    now = datetime.now()
    
    # 🧼 スマート・リセット: 朝9時前（準備時間）だけダッシュボードを掃除する
    if now.hour < 9:
        print("☀️ 朝の準備時間です。ダッシュボードをリセットなのだ！")
        send_to_gas({"action": "reset"})
    else:
        print("🕒 取引時間中、または夜間です。リセットは行わずに進むのだ。")
    
    # 起動通知
    test_msg = f"🚀 スナイパー・パトロール、クラウド上で起動したのだ！\n現在時刻: {now.strftime('%H:%M:%S')}\n監視体制に入るのだ！"
    send_notification(test_msg)
    
    # 時間帯によって動作を変える
    if now.hour == 8 and now.minute >= 50:
        # 朝のスキャン時間（本来はここでロジックを呼ぶ）
        send_notification("🌅 8:55になりました。本日の激熱銘柄をスキャンするのだ！")
        # scan_targets()
    
    live_patrol()
