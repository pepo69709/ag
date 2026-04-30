import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime

# ===========================================================================
# Sniper AI V101: The Aegis Sniper (Integrated Production Bot)
# ===========================================================================
# 構成: V100(Exhaustion) + V101(Market Filter) + Discord Notify
# 目的: 無駄なトレードを徹底排除し、最高純度のエントリーだけを通知する。
# ===========================================================================

# --- [設定] ---
DISCORD_WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK_HERE"
TICKERS = ["6857.T", "6146.T", "8035.T", "8766.T", "4063.T", "8058.T", "8306.T"] # 精鋭銘柄
SCORE_THRESHOLD = 0.65  # 0.0 ~ 1.0 (0.7以上が推奨)

class AegisSniperBot:
    def __init__(self, tickers, webhook_url):
        self.tickers = tickers
        self.webhook_url = webhook_url

    def send_notification(self, message):
        """Discordへ通知を送信"""
        if self.webhook_url == "YOUR_DISCORD_WEBHOOK_HERE":
            print(f"[LOCAL ONLY] {message}")
            return
        payload = {"content": f"🛡️ **Sniper AI V101 Alert**\n{message}"}
        try:
            requests.post(self.webhook_url, json=payload)
        except Exception as e:
            print(f"Notification Error: {e}")

    def market_regime_ok(self, ticker):
        """V101: 市場環境フィルター (ボラティリティ & トレンド強度)"""
        df = yf.download(ticker, period="10d", interval="60m", progress=False)
        if df.empty or len(df) < 50: return False
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 指標計算
        sma20 = df['Close'].rolling(20).mean().iloc[-1]
        sma50 = df['Close'].rolling(50).mean().iloc[-1]
        atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        
        # 1. ボラティリティ判定 (ATR / Price) - 死んでいる相場を排除
        atr_ratio = (atr / df['Close'].iloc[-1]) * 100
        
        # 2. トレンド強度判定 (SMA乖離) - レンジ相場を排除
        trend_strength = abs(sma20 - sma50) / sma50
        
        # 判定基準
        is_volatile = atr_ratio > 0.4    # ボラティリティが一定以上あるか
        is_trending = trend_strength > 0.002 # トレンドが一定以上出ているか
        
        return is_volatile and is_trending

    def get_signal(self, ticker):
        """V100: 個別銘柄のエントリー判定"""
        df = yf.download(ticker, period="5d", interval="60m", progress=False)
        if df.empty or len(df) < 10: return False, 0
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # トレンド
        sma20 = df['Close'].rolling(20).mean().iloc[-1]
        sma50 = df['Close'].rolling(50).mean().iloc[-1]
        trend_ok = sma20 > sma50
        
        # 3時間枯渇
        last_3_low = df['Low'].iloc[-3:].min()
        prev_low = df['Low'].iloc[-4]
        exhaustion = last_3_low >= prev_low
        
        # スコアリング (Rank Interaction)
        # 簡易的な直近20本の相対位置
        recent = df.tail(20)
        ts_val = (sma20 - sma50) / sma50
        comp_val = (recent['High'].max() - recent['Low'].min()) / df['Close'].iloc[-1]
        
        # スコア (0.0 - 1.0)
        score = np.clip(1.0 - comp_val * 10, 0, 1) * np.clip(ts_val * 50, 0, 1)
        
        return (trend_ok and exhaustion), score

    def run(self):
        print(f"[*] Loop started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        for t in self.tickers:
            try:
                # 1. 環境フィルター (盾)
                if not self.market_regime_ok(t):
                    continue
                
                # 2. 個別シグナル (矛)
                signal_ok, score = self.get_signal(t)
                
                if signal_ok and score >= SCORE_THRESHOLD:
                    msg = f"🎯 **ENTRY SIGNAL DETECTED**\nTicker: `{t}`\nScore: `{score:.2f}`\nPrice: `{yf.Ticker(t).fast_info['last_price']:.2f}`\nStatus: Market OK + Exhaustion + Trend"
                    self.send_notification(msg)
                    print(f"[!] Signal: {t} (Score: {score:.2f})")
                
            except Exception as e:
                print(f"[!] Error on {t}: {e}")

if __name__ == "__main__":
    bot = AegisSniperBot(TICKERS, DISCORD_WEBHOOK_URL)
    while True:
        # 毎時実行 (市場が開いている時間帯のみ運用を推奨)
        bot.run()
        print("[*] Waiting for next hour...")
        time.sleep(3600) # 1時間待機
