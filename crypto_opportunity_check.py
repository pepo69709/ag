import yfinance as yf
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

# ==========================================
# 💎 CRYPTO OPPORTUNITY SCANNER (1.0% Target)
# ==========================================

# ターゲット：主要な仮想通貨（ボラティリティが高いもの）
CRYPTO_LIST = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", 
    "ADA-USD", "DOGE-USD", "AVAX-USD", "DOT-USD", "LINK-USD"
]

# 1.0%達成の判定基準
PROFIT_TARGET = 1.05  # 手数料(約0.05%)を考慮して1.05%
LOOK_AHEAD_DAYS = 3   # 3日以内に達成できるか

def analyze_crypto_opportunities(period="1y"):
    print(f"🚀 【仮想通貨 1.0% チャンス調査】期間: 過去 {period}")
    print(f"対象銘柄: {', '.join(CRYPTO_LIST)}")
    print("-" * 50)
    
    total_samples = 0
    total_hits = 0
    results = []

    for ticker in CRYPTO_LIST:
        try:
            df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
            if df.empty: continue
            
            # yfinanceのマルチインデックス対策
            if isinstance(df.columns, pd.MultiIndex):
                close = df['Close'].iloc[:, 0]
                high = df['High'].iloc[:, 0]
            else:
                close = df['Close']
                high = df['High']

            # 特徴量
            sma25 = close.rolling(window=25).mean()
            dev = (close / sma25.replace(0, 1e-6) - 1) * 100
            
            # RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi = 100 - (100 / (1 + (gain / loss.replace(0, 1e-6)).fillna(0)))
            
            hits = 0
            # 未来の価格を見て「1.0%達成」をカウント
            for i in range(len(df) - LOOK_AHEAD_DAYS):
                entry_price = float(close.iloc[i])
                
                # 条件：乖離率が-3%以下、かつRSIが35以下（売られすぎ）
                if dev.iloc[i] < -3 and rsi.iloc[i] < 35:
                    total_samples += 1
                    
                    # その後3日間の最高値を確認
                    future_max = float(high.iloc[i+1:i+1+LOOK_AHEAD_DAYS].max())
                    if future_max >= entry_price * (1 + PROFIT_TARGET/100):
                        hits += 1
                        total_hits += 1
            
            results.append({
                "ticker": ticker,
                "opportunities": hits,
                "total_days": len(df)
            })
            print(f"✅ {ticker}: {hits} 回の 1.0% チャンス発見")
            
        except Exception as e:
            print(f"Error analyzing {ticker}: {e}")

    print("-" * 50)
    print(f"📊 【最終報告】")
    print(f"過去 {period} で合計 {total_hits} 回の『絶好のエントリー機会』がありました。")
    avg_per_month = total_hits / (12 if period == "1y" else 1)
    print(f"1ヶ月あたり平均: 約 {avg_per_month:.1f} 回")
    
    if total_samples > 0:
        print(f"条件合致時の期待勝率: {(total_hits / total_samples * 100):.1f}%")

if __name__ == "__main__":
    analyze_crypto_opportunities("1y")
