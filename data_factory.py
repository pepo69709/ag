"""
data_factory.py — Sniper AI V8.0 拡張データ収集
================================================
変更点:
  - 期間: 2年 → 5年 (1d)
  - 銘柄: 48銘柄 → 日経225主要100銘柄
  - 過学習対策: 銘柄ごとに独立処理・時系列順序を厳守
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from indicators import Indicators

# --- 日経225 主要100銘柄リスト ---
# セクター分散: 半導体・金融・商社・自動車・小売・通信・製薬・電機・機械・化学
NIKKEI100 = [
    # 半導体・電機精密
    "8035.T", "6920.T", "6146.T", "6857.T", "4063.T", "6501.T",
    "6702.T", "6723.T", "6752.T", "6758.T", "6981.T", "6902.T",
    "6954.T", "7733.T", "7741.T", "6971.T",
    # 自動車・輸送機
    "7203.T", "7267.T", "7269.T", "7201.T", "7261.T", "7270.T",
    "7272.T", "7011.T", "7012.T",
    # 金融・銀行・保険
    "8306.T", "8316.T", "8411.T", "8766.T", "8725.T", "8604.T",
    "8750.T", "7182.T",
    # 商社・エネルギー
    "8001.T", "8002.T", "8031.T", "8053.T", "8058.T", "5020.T",
    "5019.T",
    # 通信・IT
    "9984.T", "9432.T", "9433.T", "9434.T", "4689.T", "3659.T",
    "4755.T",
    # 小売・消費
    "9983.T", "8267.T", "7974.T", "2413.T", "3382.T", "7011.T",
    # 製薬・ヘルスケア
    "4502.T", "4503.T", "4519.T", "4568.T", "4507.T",
    # 機械・重工
    "6367.T", "6301.T", "6326.T", "7832.T", "6113.T",
    # 化学・素材
    "4183.T", "4188.T", "4204.T", "3407.T", "5401.T", "5406.T",
    # 不動産・建設
    "8802.T", "8801.T", "8830.T", "1928.T", "1925.T",
    # 食品・飲料
    "2802.T", "2503.T", "2587.T", "2269.T",
    # サービス・レジャー
    "6098.T", "4661.T", "9602.T", "9201.T",
    # ETF (レバ含む・相場全体の特性学習)
    "1458.T", "1459.T", "1357.T",
]

# 重複除去
NIKKEI100 = list(dict.fromkeys(NIKKEI100))

class DataFactory:
    def __init__(self, tickers, period="5y"):
        self.tickers = tickers
        self.period  = period

    def fetch_raw_data(self, ticker):
        try:
            df = yf.download(ticker, period=self.period,
                             interval="1d", progress=False)
            if df.empty: return None
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df[df['Volume'] > 0]
            return df.dropna()
        except Exception as e:
            print(f"  [!] Fetch error {ticker}: {e}")
            return None

    def generate_features(self, df, ticker):
        if df is None or len(df) < 250:  # 200SMAのために最低250行必要
            return None
        try:
            df = df.copy()
            df['RSI']                          = Indicators.rsi(df)
            df['MACD'], df['MACD_Signal']      = Indicators.macd(df)
            df['BB_Upper'], df['BB_Mid'], df['BB_Lower'] = Indicators.bbands(df)
            df['ATR']                          = Indicators.atr(df)
            df['ADX']                          = Indicators.adx(df)

            df['SMA_20']   = df['Close'].rolling(20).mean()
            df['SMA_50']   = df['Close'].rolling(50).mean()
            df['SMA_200']  = df['Close'].rolling(200).mean()

            df['kairi_20']  = (df['Close'] / df['SMA_20']  - 1) * 100
            df['kairi_200'] = (df['Close'] / df['SMA_200'] - 1) * 100
            df['vol_ratio'] = df['Volume'] / (df['Volume'].rolling(20).mean() + 1e-9)

            for i in range(1, 4):
                df[f'return_lag_{i}'] = df['Close'].pct_change(i)
                df[f'rsi_lag_{i}']    = df['RSI'].shift(i)

            # --- 5 New Features (V9.0) ---
            high_250 = df['High'].rolling(250).max()
            df['high_52w_ratio'] = df['Close'] / (high_250 + 1e-9)
            
            df['roc_20'] = df['Close'].pct_change(20)
            
            df['bb_position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'] + 1e-9)
            
            atr_7 = Indicators.atr(df, length=7)
            atr_30 = Indicators.atr(df, length=30)
            df['atr_compression'] = atr_7 / (atr_30 + 1e-9)
            
            vol_5 = df['Volume'].rolling(5).mean()
            vol_20 = df['Volume'].rolling(20).mean()
            df['vol_trend'] = vol_5 / (vol_20 + 1e-9)

            # --- ターゲットの現実化 (V9.8: Reality Shock) ---
            # 1. 5日後の終値リターン
            df['target_return'] = (df['Close'].shift(-5) / df['Close']) - 1
            
            # 2. 5日間のうちの最安値 (損切り判定用)
            future_lows = [df['Low'].shift(-i) for i in range(1, 6)]
            min_future_low = pd.concat(future_lows, axis=1).min(axis=1)
            df['target_low'] = (min_future_low / df['Close']) - 1
            
            # 3. 正解ラベル (1.0%以上の利益、かつ途中で -2.5% を割り込んでいない)
            df['y_clf'] = ((df['target_return'] > 0.01) & (df['target_low'] > -0.025)).astype(int)
            
            df['ticker'] = ticker
            return df.dropna()

        except Exception as e:
            print(f"  [!] Feature error {ticker}: {e}")
            return None

    def build_dataset(self, out_path="training_data_v4.csv"):
        # --- 🌐 市場全体のデータを事前に取得 (日足) ---
        print("[INFO] マクロデータ取得中 (^N225, JPY=X)...")
        n225 = yf.download("^N225", period=self.period, interval="1d", progress=False)
        jpy = yf.download("JPY=X", period=self.period, interval="1d", progress=False)
        
        # 列名の平坦化 (MultiIndex対策)
        if isinstance(n225.columns, pd.MultiIndex): n225.columns = n225.columns.get_level_values(0)
        if isinstance(jpy.columns, pd.MultiIndex): jpy.columns = jpy.columns.get_level_values(0)

        self.macro_df = pd.DataFrame(index=n225.index)

        # 日経平均の勢い (20日移動平均との乖離)
        self.macro_df['mkt_trend'] = (n225['Close'] / n225['Close'].rolling(20).mean() - 1) * 100
        # 為替の動き (5日間の変動率)
        self.macro_df['fx_roc'] = jpy['Close'].pct_change(5) * 100
        # 市場のパニック度 (日経平均の ATR / 終値 * 100)
        n225_atr = Indicators.atr(n225)
        self.macro_df['mkt_vol'] = (n225_atr / n225['Close']) * 100
        self.macro_df = self.macro_df.fillna(0)


        all_data = []
        n = len(self.tickers)
        print(f"[START] {n}銘柄 × {self.period} のデータを収集中 (マクロ指標込)...\n")

        for i, ticker in enumerate(self.tickers, 1):
            print(f"  [{i:3d}/{n}] {ticker}", end=" ... ", flush=True)
            raw  = self.fetch_raw_data(ticker)
            
            # マクロデータをマージしてから特徴量生成
            if raw is not None:
                raw = raw.join(self.macro_df, how='left')
                
            feat = self.generate_features(raw, ticker)
            if feat is not None:
                all_data.append(feat)
                print(f"OK ({len(feat)}行)")
            else:
                print("SKIP (データ不足)")

        if not all_data:
            print("[ERROR] データが一件も取得できませんでした")
            return None

        combined = pd.concat(all_data, ignore_index=False)
        combined.index = pd.to_datetime(combined.index)
        combined = combined.sort_index() # 日付順に並べ替え（時系列リーク防止）
        combined.index.name = "Date"
        combined.to_csv(out_path, index=True)


        total_rows = len(combined)
        print(f"\n[DONE] {out_path} に保存しました")
        print(f"       行数: {total_rows:,}  |  銘柄数: {len(all_data)}")
        print(f"       期間: {self.period}  |  列数: {combined.shape[1]}")
        return combined


if __name__ == "__main__":
    factory = DataFactory(NIKKEI100, period="5y")
    dataset = factory.build_dataset("training_data_v4.csv")
    if dataset is not None:
        y_clf = (dataset['target_return'] > 0.01).astype(int)
        print(f"       正解率(True): {y_clf.mean():.1%}")
        print("\n次のステップ: python ml_train.py でモデルを再訓練してください")

