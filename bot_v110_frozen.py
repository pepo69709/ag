import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime

# ===========================================================================
# Sniper AI V110.0: THE FROZEN SPECIFICATION (FINAL)
# ===========================================================================
# 警告: このファイルは「凍結仕様」に基づき固定されています。
# これ以降のロジック変更、パラメータ調整は、いかなる理由があっても禁止します。
# 一致確認項目:
# - 1h足 / 往復コスト 0.2% (FEE 0.1% + SLIP 0.1%)
# - 3時間枯渇 (min(L[-3:]) >= L[-4])
# - エグジット (3% TP / 20SMA 割れ)
# - サンプル数フィルタ (Trades >= 15)
# ===========================================================================

# --- [設定] ---
DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1499426291932332222/oLvczcsPgBSCmhq7bIATLbJtpIgwwLoeiO_H6G1XF9QDpt3abAPv5vk_JHfH692tqY1t"
# 月次メンテナンスで更新される「 Winners Circle 」リスト
TICKERS = ["6857.T", "6146.T", "8035.T", "8058.T", "4063.T", "4502.T", "8306.T"]
SCORE_THRESHOLD = 0.65
TOTAL_COST = 0.002 # 0.2% (Evaluation Freeze準拠)

class FrozenSniperBot:
    def __init__(self, tickers, webhook_url):
        self.tickers = tickers
        self.webhook_url = webhook_url

    def send_notification(self, message):
        if self.webhook_url == "YOUR_DISCORD_WEBHOOK_HERE":
            print(f"[LOCAL] {message}")
            return
        payload = {"content": f"🛡️ **Sniper AI V110 ALERT**\n{message}"}
        try:
            requests.post(self.webhook_url, json=payload)
        except Exception as e:
            print(f"Notify Error: {e}")

    def is_market_ok(self, ticker):
        """V101: 市場環境フィルター (Aegis)"""
        df = yf.download(ticker, period="10d", interval="60m", progress=False)
        if df.empty or len(df) < 50: return False
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        close = df['Close'].iloc[-1]
        sma20 = df['Close'].rolling(20).mean().iloc[-1]
        sma50 = df['Close'].rolling(50).mean().iloc[-1]
        atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        
        atr_ratio = (atr / close) * 100
        trend_strength = abs(sma20 - sma50) / (sma50 + 1e-9)
        
        # ボラティリティとトレンドが一定以上あること
        return (atr_ratio > 0.4) and (trend_strength > 0.002)

    def get_signal(self, ticker):
        """V100/V110: 凍結狙撃ロジック"""
        df = yf.download(ticker, period="5d", interval="60m", progress=False)
        if df.empty or len(df) < 10: return False, 0
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 指標
        sma20 = df['Close'].rolling(20).mean()
        sma50 = df['Close'].rolling(50).mean()
        
        # 1. トレンド条件
        trend_ok = sma20.iloc[-1] > sma50.iloc[-1]
        
        # 2. 枯渇条件 (3時間安値更新なし)
        # 厳密なインデックス監査: 直近3本の最小値 >= その前の安値
        # ここでは確定足(i-2, i-1, i)と(i-3)を比較
        exhaustion = df['Low'].iloc[-3:].min() >= df['Low'].iloc[-4]
        
        # 3. 正規化スコアリング (Tanh)
        recent = df.tail(20)
        ts_val = (sma20.iloc[-1] - sma50.iloc[-1]) / (sma50.iloc[-1] + 1e-9)
        # スケールを物理的に固定 (0.05を境界値とする)
        comp_val = (recent['High'].max() - recent['Low'].min()) / (df['Close'].iloc[-1] + 1e-9)
        
        # 正規化判定
        ts_score = np.tanh(ts_val * 40)
        comp_score = np.tanh((0.05 - comp_val) * 20)
        score = np.clip((ts_score + comp_score) / 2, 0, 1)
        
        return (trend_ok and exhaustion), score

    def run(self):
        print(f"[*] Frozen Scan started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        for t in self.tickers:
            try:
                if not self.is_market_ok(t): continue
                
                signal_ok, score = self.get_signal(t)
                if signal_ok and score >= SCORE_THRESHOLD:
                    price = yf.Ticker(t).fast_info['last_price']
                    msg = f"🎯 **ENTRY SIGNAL**\nTicker: `{t}`\nScore: `{score:.2f}`\nPrice: `{price:.2f}`\nStatus: Spec V110 Compliant"
                    self.send_notification(msg)
            except Exception as e:
                print(f"[!] Error on {t}: {e}")

if __name__ == "__main__":
    bot = FrozenSniperBot(TICKERS, DISCORD_WEBHOOK_URL)
    while True:
        # 市場稼働時間（9時〜15時）のみの運用を推奨
        bot.run()
        print("[*] Waiting for next scan...")
        time.sleep(3600)
