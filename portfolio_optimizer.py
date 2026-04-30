import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf

# --- 🏦 Sniper AI V5.1: Robust Portfolio Optimizer ---
# 役割: Ledoit-Wolf法による共分散の安定化と、リスク回避度(lambda)を用いた最適配分。

class PortfolioOptimizer:
    def __init__(self, risk_aversion=2.0, max_weight=0.15):
        self.risk_aversion = risk_aversion # λ: リスクをどれだけ嫌うか
        self.max_weight = max_weight # 1銘柄の最大配分 (15%)

    def calculate_optimal_weights(self, returns_df, target_evs, risk_aversion=None):
        """
        堅牢な平均分散最適化 (Robust Mean-Variance)
        """
        lambda_val = risk_aversion if risk_aversion is not None else self.risk_aversion
        if returns_df.empty or not target_evs:
            return {}

        tickers = returns_df.columns.tolist()
        n = len(tickers)
        
        # 1. Ledoit-Wolf法による共分散行列の推定 (ノイズを縮小して安定化)
        # これにより、データの少なさによる不安定さを解消する
        lw = LedoitWolf().fit(returns_df)
        cov_matrix = lw.covariance_ * 252 # 年率換算
        
        # 期待収益ベクトル (EV)
        mu = np.array([target_evs.get(t, 0) for t in tickers])
        
        # 2. 最適化スコアの計算
        # 目的関数: Max ( w^T * mu - lambda * w^T * Sigma * w )
        # ここでは解析的な近似解(リスク・パリティ + アルファ)を用いる
        
        # 個別リスク(ボラティリティ)
        vols = np.sqrt(np.diag(cov_matrix))
        
        # 利益(mu)からリスク(lambda * var)を引く
        risk_scores = mu - (lambda_val * (vols ** 2))
        
        # プラスのスコアを持つものだけに配分
        pos_scores = np.maximum(risk_scores, 0)
        
        if np.sum(pos_scores) == 0:
            # すべてマイナスの場合は、最もマシなものに少しだけ割り振るか、空にする
            return {t: 0 for t in tickers}

        # 3. 逆ボラティリティ重み付けとスコアの融合
        inv_vols = 1.0 / (vols + 1e-9)
        raw_weights = inv_vols * pos_scores
        
        # 正規化
        weights = raw_weights / np.sum(raw_weights)
        
        # 4. ポートフォリオ制約 (1銘柄 最大15%制限)
        # 超過分を他の銘柄に再配分する簡易アルゴリズム
        for _ in range(5): # 数回繰り返して収束させる
            excess = np.maximum(weights - self.max_weight, 0)
            if np.sum(excess) == 0: break
            
            # 上限に達していない銘柄のマスク
            under_limit = weights < self.max_weight
            if np.sum(under_limit) == 0: break
            
            # 超過分を配分
            weights = np.minimum(weights, self.max_weight)
            weights[under_limit] += np.sum(excess) * (weights[under_limit] / np.sum(weights[under_limit]))

        return dict(zip(tickers, np.round(weights, 3)))

    def analyze_correlations(self, returns_df):
        """Ledoit-Wolf推定された共分散から相関を計算"""
        lw = LedoitWolf().fit(returns_df)
        cov = lw.covariance_
        vols = np.sqrt(np.diag(cov))
        outer_vols = np.outer(vols, vols)
        corr = cov / (outer_vols + 1e-9)
        return pd.DataFrame(corr, index=returns_df.columns, columns=returns_df.columns)

if __name__ == "__main__":
    # テスト
    df = pd.DataFrame(np.random.normal(0.001, 0.02, (100, 5)), columns=['A','B','C','D','E'])
    evs = {'A': 0.1, 'B': 0.05, 'C': 0.02, 'D': 0.01, 'E': -0.05}
    opt = PortfolioOptimizer()
    w = opt.calculate_optimal_weights(df, evs)
    print(f"V5.1 Robust Weights: {w}")
