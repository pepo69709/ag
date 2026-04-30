import yfinance as yf
import pandas as pd
import os

# --- 🛰️ Sniper AI V8.0: Data Provider Interface ---
# 役割: yfinance や Moomoo API など、複数のデータソースを切り替え可能にする。

class DataProvider:
    def __init__(self, source="yfinance"):
        self.source = source

    def get_data(self, ticker, period="1y", interval="1d"):
        """
        指定されたソースから株価データを取得する
        """
        if self.source == "yfinance":
            return self._get_yfinance_data(ticker, period, interval)
        elif self.source == "moomoo":
            return self._get_moomoo_data(ticker)
        else:
            raise ValueError(f"Unknown data source: {self.source}")

    def _get_yfinance_data(self, ticker, period, interval):
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False)
            if df.empty: return None
            return df
        except Exception as e:
            print(f"yfinance error: {e}")
            return None

    def _get_moomoo_data(self, ticker):
        """
        Moomoo API (FutuOpenD) への接続用テンプレート
        ユーザーが Moomoo API キーを設定すれば、ここを有効化する
        """
        print(f"📡 Moomoo API Bridge: Connecting for {ticker}...")
        # TODO: moomoo-api-python の実装
        # 20分遅延のないリアルタイムデータを提供予定
        return self._get_yfinance_data(ticker, "1y", "1d") # 現状はフォールバック

if __name__ == "__main__":
    provider = DataProvider()
    data = provider.get_data("7203.T")
    if data is not None:
        print(f"Data retrieved: {len(data)} rows from {provider.source}")
