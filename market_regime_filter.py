import pandas as pd
import numpy as np
import yfinance as yf

# --- Sniper AI V101: Market Regime Filter ---
# 役割: 日経平均(INDEX)の状態を監視し、戦略の「発動許可」を出す司令塔。
# 目的: 市場全体の地合いが悪い時の「不運な負け」を排除し、PFを一段階引き上げる。

class MarketRegimeFilter:
    def __init__(self, index_ticker="^N225"):
        self.index_ticker = index_ticker

    def get_market_status(self, period="1mo"):
        """市場全体のレジーム(地合い)を判定する"""
        df = yf.download(self.index_ticker, period=period, interval="60m", progress=False)
        if df.empty: return "NEUTRAL"
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 1. トレンド判定 (SMA20 vs SMA50)
        df['sma20'] = df['Close'].rolling(20).mean()
        df['sma50'] = df['Close'].rolling(50).mean()
        
        # 2. 強弱判定 (ADX簡易版: 直近の方向性)
        curr_price = df['Close'].iloc[-1]
        sma20 = df['sma20'].iloc[-1]
        sma50 = df['sma50'].iloc[-1]
        
        # レジーム定義
        if curr_price > sma20 > sma50:
            return "BULLISH_TREND" # 積極参戦
        elif curr_price < sma20 < sma50:
            return "BEARISH_CRASH" # 参戦見合わせ (暴落リスク)
        elif abs(sma20 - sma50) / sma50 < 0.005:
            return "CHOPPY_RANGE"  # 慎重に (持ち合い)
        else:
            return "NEUTRAL"

    def apply_filter(self, ticker_signal, market_regime):
        """シグナルと市場環境を照合して、最終的なGOを出す"""
        if market_regime == "BEARISH_CRASH":
            return False, "Market Crash Prevention"
        if market_regime == "CHOPPY_RANGE":
            # 持ち合い時はより厳しい条件が必要
            return ticker_signal, "Tight Filter Mode"
        return ticker_signal, "Full Throttle"

# --- V101 統合イメージ ---
# if __name__ == "__main__":
#     regime = MarketRegimeFilter().get_market_status()
#     print(f"Current Market Regime: {regime}")
#     
#     can_trade, reason = MarketRegimeFilter().apply_filter(True, regime)
#     if can_trade:
#         print(f"Execute Sniper: {reason}")
#     else:
#         print(f"Brake Engaged: {reason}")
