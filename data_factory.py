import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from indicators import Indicators

# --- 🏭 Sniper AI V4.0: Data Factory (v2) ---
# Python 3.14 互換モード

class DataFactory:
    def __init__(self, tickers):
        self.tickers = tickers

    def fetch_raw_data(self, ticker):
        try:
            df = yf.download(ticker, period="2y", interval="1d", progress=False)
            if df.empty: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            df = df[df['Volume'] > 0]
            return df.dropna()
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            return None

    def generate_features(self, df):
        if df is None or len(df) < 50: return None
        
        # 特徴量生成 (indicators.py を使用)
        df['RSI'] = Indicators.rsi(df)
        df['MACD'], df['MACD_Signal'] = Indicators.macd(df)
        df['BB_Upper'], df['BB_Mid'], df['BB_Lower'] = Indicators.bbands(df)
        df['ATR'] = Indicators.atr(df)
        df['ADX'] = Indicators.adx(df)
        
        # カスタム特徴量
        df['SMA_20'] = df['Close'].rolling(20).mean()
        df['SMA_50'] = df['Close'].rolling(50).mean()
        df['SMA_200'] = df['Close'].rolling(200).mean()
        
        df['kairi_20'] = (df['Close'] / df['SMA_20'] - 1) * 100
        df['kairi_200'] = (df['Close'] / df['SMA_200'] - 1) * 100
        df['vol_ratio'] = df['Volume'] / df['Volume'].rolling(5).mean()
        
        # ラグ特徴量
        for i in range(1, 4):
            df[f'return_lag_{i}'] = df['Close'].pct_change(i)
            df[f'rsi_lag_{i}'] = df['RSI'].shift(i)

        # ターゲット: 5営業日後の対数収益率
        df['target_return'] = np.log(df['Close'].shift(-5) / df['Close'])
        
        return df.dropna()

    def build_dataset(self):
        full_dataset = []
        print(f"Building V4.0 Intelligence Dataset (Python 3.14 Safe)...")
        
        for ticker in self.tickers:
            raw = self.fetch_raw_data(ticker)
            processed = self.generate_features(raw)
            if processed is not None:
                processed['ticker'] = ticker
                full_dataset.append(processed)
        
        if not full_dataset: return None
        return pd.concat(full_dataset)

if __name__ == "__main__":
    from core import TICKER_LIST
    factory = DataFactory(TICKER_LIST[:20])
    dataset = factory.build_dataset()
    if dataset is not None:
        dataset.to_csv("training_data_v4.csv", index=True)
        print(f"Dataset Ready: {dataset.shape[0]} samples, {dataset.shape[1]} features.")
    else:
        print("Dataset generation failed.")

