import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from core import TICKER_LIST, SniperCoreV42

# --- V20.0: Training Data Generator ---
# 役割: 物理フィルターを通過した候補を抽出し、文脈(特徴量)と結果(ラベル)を記録。

def generate_training_data(days=30):
    print(f"[*] Generating Training Data for V20.0 (Past {days} days)...")
    interval = "5m"
    data = yf.download(TICKER_LIST, period="1mo", interval=interval, group_by='ticker', progress=False)
    
    samples = []
    for ticker in TICKER_LIST:
        df = data[ticker]
        for i in range(50, len(df)-40): # エグジット判定用に少し余裕を残す
            try:
                slice_df = df.iloc[i-50:i]
                if slice_df.isnull().values.any(): continue
                
                # --- 物理フィルター(V19.8) ---
                close = slice_df['Close'].iloc[-1]
                vol = slice_df['Close'].pct_change().rolling(20).std().iloc[-1]
                high_10 = slice_df['High'].rolling(10).max().iloc[-1]
                pullback = (high_10 - close) / (high_10 + 1e-9)
                recent_surge = slice_df['Close'].pct_change(10).iloc[-1]
                
                pb_ratio = pullback / (vol + 1e-9)
                if pb_ratio < 0.8: continue
                if recent_surge > (vol * 3.5): continue
                if vol < 0.003: continue
                
                # --- 特徴量(文脈)の生成 ---
                ma_20 = slice_df['Close'].rolling(20).mean()
                ma_slope = (ma_20.iloc[-1] - ma_20.iloc[-5]) / (ma_20.iloc[-5] + 1e-9)
                rsi = Indicators_calc_rsi(slice_df) # 簡易RSI
                vol_spike = slice_df['Volume'].iloc[-1] / (slice_df['Volume'].rolling(20).mean().iloc[-1] + 1e-9)
                
                # --- ラベル(結果)の算出 ---
                # 180分後の価格変化
                future_prices = df['Close'].iloc[i+1 : i+37] # 5m * 36 = 180m
                if future_prices.empty: continue
                
                # 簡易的なエグジットシミュレーション
                max_ret = (future_prices.max() / close) - 1
                min_ret = (future_prices.min() / close) - 1
                
                # ラベル定義: 損切り(-2%)にかからず、1%以上の利益が出たか
                label = 1 if max_ret > 0.01 and min_ret > -0.02 else 0
                
                samples.append({
                    "ticker": ticker,
                    "pb_ratio": pb_ratio,
                    "surge_ratio": recent_surge / (vol + 1e-9),
                    "volatility": vol,
                    "ma_slope": ma_slope,
                    "rsi": rsi,
                    "vol_spike": vol_spike,
                    "label": label
                })
            except: continue
            
    train_df = pd.DataFrame(samples)
    train_df.to_csv("v20_train_data.csv", index=False)
    print(f"[*] Success: Generated {len(train_df)} samples in 'v20_train_data.csv'")

def Indicators_calc_rsi(df, period=14):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs.iloc[-1]))

if __name__ == "__main__":
    generate_training_data()
