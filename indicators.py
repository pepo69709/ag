import pandas as pd
import numpy as np

# --- 📐 Sniper AI V4.0: Pro Indicators ---
# 役割: pandas/numpyのみを使用し、外部ライブラリに依存しない高速テクニカル指標計算。

class Indicators:
    @staticmethod
    def rsi(df, length=14):
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
        rs = gain / (loss + 1e-9)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(df, fast=12, slow=26, signal=9):
        exp1 = df['Close'].ewm(span=fast, adjust=False).mean()
        exp2 = df['Close'].ewm(span=slow, adjust=False).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        return macd_line, signal_line

    @staticmethod
    def bbands(df, length=20, std_dev=2):
        sma = df['Close'].rolling(window=length).mean()
        std = df['Close'].rolling(window=length).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return upper, sma, lower

    @staticmethod
    def atr(df, length=14):
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        return true_range.rolling(window=length).mean()

    @staticmethod
    def volume_spike(df, window=20):
        """直近平均に対する出来高の倍率"""
        avg_vol = df['Volume'].rolling(window).mean()
        return df['Volume'] / (avg_vol + 1e-9)

    @staticmethod
    def vwap_divergence(df):
        """VWAP（売買高加重平均価格）からの乖離率"""
        # 簡易的な1日VWAP (Typical Price * Volume)
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        vwap = (tp * df['Volume']).rolling(20).sum() / (df['Volume'].rolling(20).sum() + 1e-9)
        return (df['Close'] / vwap - 1) * 100

    @staticmethod
    def gap_rate(df):
        """前日終値に対する当日始値のギャップ率"""
        return (df['Open'] / df['Close'].shift(1) - 1) * 100

    @staticmethod
    def volume_acceleration(df, window=5):
        """出来高の加速（変化率の変化）"""
        vol_change = df['Volume'].pct_change(window)
        return vol_change.diff(window)

    @staticmethod
    def relative_strength(df, benchmark_df, window=14):
        """ベンチマーク（日経平均等）に対する相対的な強さのモメンタム"""
        # 価格比のモメンタム
        ratio = df['Close'] / (benchmark_df['Close'] + 1e-9)
        rs = (ratio / ratio.shift(window) - 1) * 100
        return rs

    @staticmethod
    def adx(df, length=14):
        """ADX (トレンドの強さ) の簡易実装"""
        plus_dm = df['High'].diff()
        minus_dm = df['Low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        tr = Indicators.atr(df, length)
        plus_di = 100 * (plus_dm.ewm(alpha=1/length).mean() / tr)
        minus_di = 100 * (np.abs(minus_dm).ewm(alpha=1/length).mean() / tr)
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)
        return dx.ewm(alpha=1/length).mean()

    @staticmethod
    def detect_vcp(df, window=20):
        """ボラティリティ収縮パターン(VCP)を検知する"""
        if len(df) < window: return 0.0
        # ATRの推移を計算
        atr_series = Indicators.atr(df, 14).tail(window)
        # ATRが右肩下がり（収縮）しているか、線形回帰の傾きで判定
        slope = np.polyfit(range(window), atr_series, 1)[0]
        vcp_factor = 1.0 if slope < 0 else 0.0
        # 収縮率を掛ける（最初と最後の比率）
        reduction_ratio = atr_series.iloc[0] / (atr_series.iloc[-1] + 1e-9)
        return vcp_factor * reduction_ratio

    @staticmethod
    def get_pattern_score(df):
        """チャートの『形』を100点満点でスコアリングする"""
        if len(df) < 10: return 0.0
        vcp = Indicators.detect_vcp(df)

        
        # Bull Flag 判定 (10日前までの急騰後の横ばい)
        price_spike = (df['Close'].iloc[-1] / df['Close'].iloc[-10] - 1) > 0.05
        low_vol = Indicators.atr(df, 14).iloc[-1] < Indicators.atr(df, 14).iloc[-5]
        
        score = vcp * 40 # VCPが効いていれば最大40点
        if price_spike and low_vol:
            score += 40 # Bull Flag Bonus
        
        # 52週高値近辺か (Minerviniの条件)
        high_52w = df['High'].tail(250).max()
        if df['Close'].iloc[-1] > high_52w * 0.9:
            score += 20
            
        return round(min(score, 100), 1)
