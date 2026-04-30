import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# --- Sniper AI V108: Adaptive Regime Sniper ---
# 役割: 銘柄の「今」の状態(Regime)をリアルタイムで判定し、最適な戦略を自動選択する。
# 目的: 銘柄固定の限界を突破し、あらゆる銘柄の「最も美味しい瞬間」だけを狙撃する。

class AdaptiveSniper:
    def __init__(self, tickers):
        self.tickers = tickers

    def run_adaptive_scan(self):
        print(f"[*] Starting Adaptive Regime Scan at {datetime.now().strftime('%H:%M:%S')}")
        results = []
        
        for t in self.tickers:
            try:
                # 直近60本のデータを取得 (判定用 + 実行用)
                df = yf.download(t, period="10d", interval="60m", progress=False)
                if len(df) < 50: continue
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                
                # 1. リアルタイム・レジーム判定 (直近24時間)
                recent = df.tail(24).copy()
                ret = recent['Close'].pct_change()
                vol = ret.std()
                trend = abs(recent['Close'].iloc[-1] / recent['Close'].iloc[0] - 1)
                
                regime = self._classify_regime(vol, trend)
                
                # 2. ロジックの選択と実行
                signal = False
                strategy_name = "NONE"
                
                if regime == "HIGH_ENERGY":
                    signal = self._strategy_breakout(df)
                    strategy_name = "Breakout"
                elif regime == "MID_FLOW":
                    signal = self._strategy_dip_sniper(df)
                    strategy_name = "Exhaustion Dip"
                
                results.append({
                    "Ticker": t,
                    "Regime": regime,
                    "Strategy": strategy_name,
                    "Signal": "BUY_SIGNAL" if signal else "Watching",
                    "Vol": f"{vol:.4f}",
                    "Trend": f"{trend:.4f}"
                })
            except Exception as e:
                print(f"[!] Error on {t}: {e}")

        self._report(results)

    def _classify_regime(self, vol, trend):
        """ボラティリティとトレンドから『今』の状態を定義"""
        if vol > 0.008 and trend > 0.02:
            return "HIGH_ENERGY"
        elif vol > 0.004:
            return "MID_FLOW"
        else:
            return "LOW_NOISE"

    def _strategy_breakout(self, df):
        """HIGHレジーム用: 直近20時間の高値更新を狙う"""
        return df['Close'].iloc[-1] >= df['High'].iloc[-21:-1].max()

    def _strategy_dip_sniper(self, df):
        """MIDレジーム用: 3時間安値更新なし+SMA20上を狙う(V100)"""
        sma20 = df['Close'].rolling(20).mean().iloc[-1]
        exhaustion = df['Low'].iloc[-3:].min() >= df['Low'].iloc[-4]
        return (df['Close'].iloc[-1] > sma20) and exhaustion

    def _report(self, results):
        res_df = pd.DataFrame(results)
        print("\n" + "="*85)
        print("ADAPTIVE REGIME REPORT: REAL-TIME STRATEGY SWITCHING")
        print("="*85)
        print(res_df.to_string(index=False))
        print("-" * 85)
        print("Note: Logic switches automatically based on last 24h market structure.")
        print("="*85)

if __name__ == "__main__":
    from core import TICKER_LIST
    bot = AdaptiveSniper(TICKER_LIST)
    bot.run_adaptive_scan()
