import numpy as np

# --- 🛡️ Sniper AI V4.3: Institutional Risk Engine ---
# 役割: 取引コスト(スリッページ等)を厳格に算入し、ケリー基準を5%にキャップする。

class RiskEngine:
    def __init__(self, kelly_fraction=0.2, max_position_size=0.05):
        self.kelly_fraction = kelly_fraction 
        self.max_position_size = max_position_size # 5% キャップ
        self.transaction_cost = 0.002 # 往復コスト (0.2% = 0.002)

    def calculate_kelly(self, win_rate, profit_factor=1.1):
        """校正された勝率に基づくケリー比率 (5%制限)"""
        p = win_rate
        b = profit_factor
        f_star = (p * b - (1 - p)) / (b + 1e-9)
        # ケリーの20%を使用し、さらに全体資産の5%を上限とする
        safe_f = f_star * self.kelly_fraction
        return min(max(0, safe_f), self.max_position_size)

    def get_stop_loss(self, current_price, atr, k=2.5):
        """ATRに基づいた動的な損切りライン"""
        return current_price - (atr * k)

    def get_dynamic_tp(self, atr, k=2.0):
        """ATRに基づいた動的な利食い（Take Profit）ライン
        現在価格からATRの k 倍だけ上昇した価格を目安にします。"""
        return atr * k

    def get_dynamic_sl(self, atr, k=2.5):
        """ATRに基づいた動的な損切りライン（Stop Loss）
        ATRの k 倍を損失幅として設定します。"""
        return atr * k

    def calculate_true_ev(self, current_price, pred_return, win_prob, atr, k=2.5):
        """
        真の期待値 (V4.3 Institutional)
        EV = (P * Gain) - ((1 - P) * Loss) - Transaction_Cost
        """
        gain = pred_return
        loss = (atr * k) / (current_price + 1e-9)
        
        # 利益、損失、そしてコストをすべて考慮
        ev = (win_prob * gain) - ((1 - win_prob) * loss) - self.transaction_cost
        return ev

    def get_risk_adjusted_score(self, ev):
        """期待値に基づく最終スコア化 (EV 1.5% = 100点 くらいの厳格さ)"""
        # より厳しい基準にスケーリング
        score = min(max(ev * 1500, 0), 100) 
        return int(score)
