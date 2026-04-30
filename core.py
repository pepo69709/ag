import pandas as pd
import numpy as np
import lightgbm as lgb
import os
import joblib
from indicators import Indicators
from risk_engine import RiskEngine

# --- 🚀 Sniper AI V4.2: The Final Calibrated Core ---

TICKER_LIST = [
    "1458.T", "1459.T", "1357.T", "8035.T", "4063.T", "6501.T", "6920.T", 
    "6146.T", "9984.T", "9983.T", "7203.T", "6758.T", "8001.T", "8306.T", 
    "9432.T", "7974.T", "9101.T", "8411.T", "4661.T", "4502.T", "6367.T",
    "6098.T", "2802.T", "4503.T", "8802.T", "8058.T", "8766.T", "6902.T",
    "6981.T", "7741.T", "7267.T", "4568.T", "6857.T", "6723.T", "6301.T",
    "4901.T", "8031.T", "8267.T", "9022.T", "9501.T", "9502.T", "9503.T",
    "9989.T", "3382.T", "4061.T", "4151.T", "4523.T", "6503.T"
]

class SniperCoreV42:
    def __init__(self):
        import pickle
        # V9.1: 新しい3指標モデルをロード
        with open("models/model_lgbm.pkl", "rb") as f: self.reg_model = pickle.load(f)
        with open("models/model_ridge.pkl", "rb") as f: self.ridge_model = pickle.load(f)
        with open("models/model_clf.pkl", "rb") as f: self.calibrated_clf = pickle.load(f)
        self.risk_engine = RiskEngine()

    def get_market_regime(self):
        import yfinance as yf
        n225 = yf.download("^N225", period="1y", progress=False)
        if isinstance(n225.columns, pd.MultiIndex): n225.columns = n225.columns.get_level_values(0)
        curr = n225['Close'].iloc[-1]
        ma200 = n225['Close'].rolling(200).mean().iloc[-1]
        
        # RSI計算
        delta = n225['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain / (loss + 1e-9)))).iloc[-1]
        
        regime = "BULL" if curr > ma200 else "BEAR"
        return regime, curr, rsi

    def predict_v42(self, ticker, df_hist, df_benchmark=None):
        """V6.1: Market Breathing & Uncertainty Logic"""
        df = df_hist.copy()
        
        # --- 呼吸系インジケーターの追加 ---
        df['RSI'] = Indicators.rsi(df)
        df['ATR'] = Indicators.atr(df)
        df['vol_spike'] = Indicators.volume_spike(df)
        
        # --- 🌪️ V6.3 Structural Alpha ---
        df['vwap_div'] = Indicators.vwap_divergence(df)
        df['gap_rate'] = Indicators.gap_rate(df)
        df['vol_accel'] = Indicators.volume_acceleration(df)
        
        # 日経平均との相対力 (RS)
        if df_benchmark is not None:
            df['rs_n225'] = Indicators.relative_strength(df, df_benchmark)
        else:
            df['rs_n225'] = 0
            
        # 特徴量一貫性のために、既存の名称(vol_ratio)にスパイクを代入
        df['vol_ratio'] = df['vol_spike'] 
        for i in range(1, 4):
            df[f'return_lag_{i}'] = df['Close'].pct_change(i)
            df[f'rsi_lag_{i}'] = df['RSI'].shift(i)
            
        # --- 🧠 V9.1: Feature Sync with Trainer ---
        X = np.array([[df['RSI'].iloc[-1], df['ATR'].iloc[-1], df['vol_spike'].iloc[-1]]])
        curr_price = df['Close'].iloc[-1]
        atr = df['ATR'].iloc[-1]
        
        # 1. 回帰予測 (アンサンブル)
        pred_lgbm = self.reg_model.predict(X)[0]
        pred_ridge = self.ridge_model.predict(X)[0]
        
        # アンサンブル平均
        pred_return = (pred_lgbm + pred_ridge) / 2
        
        # --- 🧠 V9.0 Confidence (Reliability) Scoring ---
        # モデル間の不一致度を再計算 (Disagreement)
        diff = abs(pred_lgbm - pred_ridge)
        # 期待リターンに対する相対的な乖離 (分母に1%のバイアスを加えて安定化)
        rel_diff = diff / (abs(pred_return) + 0.01) 
        # 信頼度: 乖離が小さいほど指数関数的に高くなるように変更 (V9.1)
        confidence = np.exp(-rel_diff * 3)
        
        # 2. 分類予測 & 確率校正 (本物の勝率を取得)
        win_prob = self.calibrated_clf.predict_proba(X)[0][1]
        
        # 信頼度が極端に低い場合は、期待値を制動
        if confidence < 0.2:
            win_prob *= 0.7 
            print(f"[LOW CONFIDENCE] for {ticker}: Disagreement is high. Throttling EV.")
        
        # --- 🛡️ V6.2 Continuous Uncertainty Penalty ---
        # 連続的な抑制: ATRが過去平均より高いほど、滑らかに勝率を削る
        atr_avg = df['ATR'].rolling(50).mean().iloc[-1]
        vol_heat = min(2.0, atr / (atr_avg + 1e-9))
        if vol_heat > 1.2:
            # 1.2倍からペナルティ開始、最大20%減衰
            penalty = (vol_heat - 1.2) * 0.25 
            win_prob *= (1.0 - penalty)
            print(f"[MARKET HEAT] detected for {ticker} ({vol_heat:.1f}x): Penalty {penalty*100:.1f}% applied.")
        
        # 3. 真の期待値 (True EV) の算出
        # V9.5: win_prob への過度な依存を避け、予測リターンと確信度の積に変更 (±10% クランプ)
        true_ev = np.clip(pred_return * confidence, -0.1, 0.1)
        # パターンスコアの算出 (VCP・Bull Flag 等)
        pattern_score = Indicators.get_pattern_score(df)
        
        # --- 🤖 V9.1: Mechanical Rule Engine (Confidence-First) ---
        mechanical_rule = "SKIP"

        # 信頼度を主導フィルターとし、確信度が高い銘柄の中で選別
        if confidence > 0.55 and pattern_score > 60:
            if true_ev > 0.02:
                mechanical_rule = "🎯 STRONG ENTRY"
            else:
                mechanical_rule = "⚠️ CAUTIOUS ENTRY"
        # 検討: WAIT/PROBING (EVがプラスなら)
        elif true_ev > 0:
            mechanical_rule = "📡 WAIT/PROBING"

        # 4. スコア化
        score = self.risk_engine.get_risk_adjusted_score(true_ev)

        # 5. 資金管理 (ケリー基準)
        kelly_size = self.risk_engine.calculate_kelly(win_rate=win_prob)
        stop_loss = self.risk_engine.get_stop_loss(curr_price, atr)

        # Exit判定
        dynamic_tp = self.risk_engine.get_dynamic_tp(atr)
        dynamic_sl = self.risk_engine.get_dynamic_sl(atr)

        # --- V18.6: 物理フィルター用指標 ---
        # 直近10本の高値
        high_10 = df['High'].rolling(10).max().iloc[-1]
        # 押し目幅: 直近高値からの下落率
        pullback = (high_10 - df['Close'].iloc[-1]) / (high_10 + 1e-9)
        # 直近の急騰率 (10分間)
        recent_surge = df['Close'].pct_change(10).iloc[-1]

        return {
            "score": score + (pattern_score * 0.05),
            "pred_return": pred_return,
            "win_prob": win_prob,
            "confidence": confidence,
            "kelly_size": kelly_size,
            "stop_loss": round(stop_loss, 1),
            "true_ev": true_ev,
            "pattern_score": pattern_score,
            "mechanical_rule": mechanical_rule,
            "pullback": pullback,
            "recent_surge": recent_surge
        }

# --- 互換用ラッパー ---
core_v42 = SniperCoreV42()

def setup_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_market_regime():
    return core_v42.get_market_regime()

def calculate_v4_score(ticker, df_hist):
    return core_v42.predict_v42(ticker, df_hist)
