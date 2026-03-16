import yfinance as yf
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import config

# ==========================================
# 💎 JAPAN STOCK OPPORTUNITY CHECK (1.0% Target)
# ==========================================

# ターゲット：日本個人投資家向けの監視500銘柄
TICKERS = config.WATCH_LIST[:500] if hasattr(config, 'WATCH_LIST') else []

PROFIT_TARGET = 1.0  # 1.0%
LOOK_AHEAD_DAYS = 5   # 日本株は5日以内のリバウンドを想定

def analyze_jp_opportunities(period="1y"):
    print(f"🚀 【日本株 1.0% チャンス調査】期間: 過去 {period}")
    print(f"対象銘柄数: {len(TICKERS)} 銘柄")
    print("-" * 50)
    
    total_samples = 0
    total_hits = 0
    
    # チャンク分けして取得
    chunk_size = 50
    for i in range(0, len(TICKERS), chunk_size):
        chunk = TICKERS[i:i+chunk_size]
        try:
            df_all = yf.download(" ".join(chunk), period=period, interval="1d", group_by='ticker', progress=False, auto_adjust=True)
            
            for ticker in chunk:
                df = df_all[ticker] if len(chunk) > 1 else df_all
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
                
                # 未来の価格を見て「1.0%達成」をカウント
                for j in range(len(df) - LOOK_AHEAD_DAYS):
                    entry_price = float(close.iloc[j])
                    
                    # 条件：乖離率が-3%以下、かつRSIが35以下（売られすぎ）
                    # 注：日本株の方が厳しい条件が必要かもしれないが、今は仮想通貨と同じ条件で比較
                    if dev.iloc[j] < -3 and rsi.iloc[j] < 35:
                        total_samples += 1
                        
                        # その後5日間の最高値を確認
                        future_max = float(high.iloc[j+1:j+1+LOOK_AHEAD_DAYS].max())
                        if future_max >= entry_price * (1 + PROFIT_TARGET/100):
                            total_hits += 1
            
            print(f"✅ 進捗: {min(i+chunk_size, len(TICKERS))}/{len(TICKERS)} 銘柄完了")
            
        except Exception as e:
            print(f"Error in chunk starting {i}: {e}")

    print("-" * 50)
    print(f"📊 【最終報告：日本株 500銘柄 vs 仮想通貨 10銘柄】")
    print(f"日本株 500銘柄の年間チャンス合計: {total_hits} 回")
    
    market_days = 245 # 年間の市場稼働日
    avg_per_day = total_hits / market_days
    print(f"1日あたり平均: 約 {avg_per_day:.1f} 回")
    
    if total_samples > 0:
        print(f"条件合致時のストレート勝率: {(total_hits / total_samples * 100):.1f}%")

if __name__ == "__main__":
    analyze_jp_opportunities("1y")
