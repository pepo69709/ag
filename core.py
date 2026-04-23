import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import sys
import io

# --- 🏹 Sniper AI: Core Module V3.1 ---
# すべてのスクリプトで共有される「心臓部」。
# V3.1: 短期指標の追加 & 地合い判定の解像度向上（急なショック対応）

def get_market_regime():
    """日経225とTOPIXの状況から、マーケット・レジームを高精度で判定する"""
    try:
        n225 = yf.download("^N225", period="1y", progress=False)
        if n225.empty or len(n225) < 200:
            return "BULL"

        if isinstance(n225.columns, pd.MultiIndex):
            n225.columns = n225.columns.get_level_values(0)

        close = n225['Close']
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        # --- 長期トレンド ---
        ma200 = close.rolling(200).mean().iloc[-1]
        ma25  = close.rolling(25).mean().iloc[-1]
        curr  = close.iloc[-1]

        # --- RSI(14) ---
        delta = close.diff()
        gain  = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi   = (100 - (100 / (1 + (gain / (loss + 1e-9))))).iloc[-1]

        # --- ボラティリティ (20日 vs 5日): ショック検知 ---
        vol20 = close.pct_change().rolling(20).std().iloc[-1] * 100
        vol5  = close.pct_change().rolling(5).std().iloc[-1]  * 100

        # ★ 急騰ショック検知: 直近5日のボラが20日平均の1.8倍を超えたら即VOLATILE
        if vol5 > vol20 * 1.8:
            print(f"⚠️ ボラティリティ・スパイク検知！ (5d={vol5:.2f}% vs 20d={vol20:.2f}%)")
            return "VOLATILE"

        # ★ 短期デッドクロス: 25日線を割り込んでいたらBEARの疑い強
        short_bear = curr < ma25

        if vol20 > 1.5:
            return "VOLATILE"
        if short_bear and curr < ma200:
            return "BEAR"
        if 45 <= rsi <= 55:
            return "FLAT"
        return "BULL" if curr > ma200 else "BEAR"

    except Exception as e:
        print(f"Regime detection error: {e}")
        return "BULL"  # デフォルト


TICKER_LIST = [
    "1357.T", "1459.T",  # Bear Market Defense (Inverse ETFs)
    # --- Major Blue Chips (Top Liquidity) ---
    "7203.T", "6758.T", "9984.T", "8035.T", "4063.T", "6501.T", "8001.T", "8306.T", "9432.T", "7974.T",
    "9983.T", "9101.T", "4502.T", "6954.T", "6702.T", "7267.T", "8058.T", "8316.T", "4568.T", "6902.T",
    "6723.T", "6503.T", "6752.T", "6857.T", "6981.T", "7741.T", "7733.T", "4911.T", "2502.T", "1605.T",
    "8031.T", "8801.T", "9020.T", "9501.T", "6301.T", "1925.T", "1801.T", "3402.T", "4503.T", "5401.T",
    "6701.T", "7011.T", "6367.T", "2802.T", "4519.T", "6098.T", "6861.T", "8053.T", "8766.T", "9022.T",
    # --- Expansion: Sector Leaders & High Volatility ---
    "6920.T", "6146.T", "6326.T", "7201.T", "8411.T", "8308.T", "8304.T", "8604.T", "8601.T", "8725.T",
    "8750.T", "8267.T", "3382.T", "9843.T", "7532.T", "2503.T", "2801.T", "2269.T", "3092.T", "4452.T",
    "4507.T", "4523.T", "4578.T", "4661.T", "4755.T", "4901.T", "5020.T", "5108.T", "5201.T", "5332.T",
    "5713.T", "5802.T", "6178.T", "6305.T", "6472.T", "6504.T", "6506.T", "6645.T",
    "6762.T", "6841.T", "6971.T", "6976.T", "7012.T", "7013.T", "7202.T", "7261.T", "7269.T",
    "7270.T", "7272.T", "7731.T", "7751.T", "7832.T", "7911.T", "7912.T", "7951.T", "8002.T",
    "8233.T", "8630.T", "8802.T", "8830.T", "9001.T", "9005.T", "9007.T", "9008.T", "9009.T", "9021.T",
    "9104.T", "9107.T", "9201.T", "9202.T", "9433.T", "9434.T", "9502.T", "9503.T", "9602.T",
    "9735.T", "9766.T"
]


def setup_terminal():
    """Windows環境での文字化け対策（多重呼び出しを防止）"""
    if sys.platform == 'win32':
        if isinstance(sys.stdout, io.TextIOWrapper) and sys.stdout.encoding.lower() == 'utf-8':
            return
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def get_indicators(df):
    """テクニカル指標の計算（全スクリプト共通）
    V3.1追加: rsi_short(5日), kairi_short(5日) による短期センサー
    """
    if df is None or len(df) < 30:
        return None

    # --- RSI (14日) ---
    delta = df['Close'].diff()
    gain  = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs    = gain / (loss + 1e-9)
    df['rsi'] = 100 - (100 / (1 + rs))

    # ★ RSI (5日) 短期センサー
    gain5  = (delta.where(delta > 0, 0)).rolling(window=5).mean()
    loss5  = (-delta.where(delta < 0, 0)).rolling(window=5).mean()
    rs5    = gain5 / (loss5 + 1e-9)
    df['rsi_short'] = 100 - (100 / (1 + rs5))

    # --- 乖離率 (25日) ---
    df['ma25']  = df['Close'].rolling(window=25).mean()
    df['kairi'] = ((df['Close'] - df['ma25']) / df['ma25']) * 100

    # ★ 乖離率 (5日) 短期センサー
    df['ma5']         = df['Close'].rolling(window=5).mean()
    df['kairi_short'] = ((df['Close'] - df['ma5']) / df['ma5']) * 100

    # --- ボラティリティ (リターンベース 20日) ---
    df['sigma'] = df['Close'].pct_change().rolling(window=20).std() * 100

    # --- 出来高倍率 ---
    df['vol_ma']    = df['Volume'].rolling(window=5).mean()
    df['vol_ratio'] = df['Volume'] / (df['vol_ma'] + 1e-9)

    return df


def load_weights():
    """最新の重みをロード"""
    path = "model_weights.json"
    if not os.path.exists(path):
        return {
            "regime_bull": {
                "rsi_weight": 0.3, "kairi_weight": 0.2,
                "vol_weight": 0.5, "sigma_filter": 1.0,
                "short_weight": 0.0  # 短期指標の重み（デフォルト0）
            },
            "regime_bear": {
                "rsi_weight": 0.6, "kairi_weight": 0.3,
                "vol_weight": 0.1, "sigma_filter": 0.8,
                "short_weight": 0.0
            },
            "regime_volatile": {
                "rsi_weight": 0.2, "kairi_weight": 0.1,
                "vol_weight": 0.2, "sigma_filter": 0.5,
                "short_weight": 0.5  # VOLATILEは短期指標を最優先
            }
        }
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_score(ticker, row, weights, regime):
    """銘柄タイプに応じてスコアリングロジックを振り分ける（Safety Interlock）"""
    # インバース判定
    is_inverse = ticker in ["1357.T", "1459.T"]

    # セーフティロック
    if regime == "BULL" and is_inverse:
        return 5
    if regime in ["BEAR", "VOLATILE"] and not is_inverse:
        # VOLATILEの場合は極端には下げない（ショック後のリバウンド狙いも有効）
        return 15 if regime == "VOLATILE" else 10

    # 地合いに応じた重みセットの取得
    regime_key = f"regime_{regime.lower()}"
    if regime_key not in weights:
        regime_key = "regime_bull"
    w = weights[regime_key]

    score = 40

    # === 長期指標 ===
    if row['rsi'] < 30:
        score += 20 * (w.get("rsi_weight", 0.3) / 0.3)
    if row['kairi'] < -10:
        score += 20 * (w.get("kairi_weight", 0.2) / 0.2)
    if row['vol_ratio'] > 1.5:
        score += 15 * (w.get("vol_weight", 0.5) / 0.5)

    # ★ 短期センサー（急落後リバウンド狙い / ショック時に特に有効）
    short_w = w.get("short_weight", 0.0)
    if short_w > 0:
        if row.get('rsi_short', 50) < 25:  # 超短期売られすぎ
            score += 15 * (short_w / 0.5)
        if row.get('kairi_short', 0) < -5:  # 直近5日で急落
            score += 10 * (short_w / 0.5)

    return int(min(max(score, 5), 100))
