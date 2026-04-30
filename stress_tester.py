import numpy as np
import pandas as pd
import os
import json

# --- 🧪 Sniper AI V8.3: Portfolio Stress Tester ---
# 役割: モンテカルロ・シミュレーションにより、暴落時の最大損失(VaR)を算出する。

class StressTester:
    def __init__(self, portfolio_file="portfolio.csv", db_file="database.csv"):
        self.portfolio_file = portfolio_file
        self.db_file = db_file

    def run_simulation(self, n_sims=1000, days=5):
        print(f"🧪 Running {n_sims} Monte Carlo Simulations for Black Swan Analysis...")
        
        if not os.path.exists(self.portfolio_file): return {"error": "No portfolio"}
        
        # ポートフォリオ読み込み
        pdf = pd.read_csv(self.portfolio_file)
        db = pd.read_csv(self.db_file)
        
        # 各銘柄の直近ボラティリティと現在値を取得
        # (ここでは簡略化のため、1日の標準偏差を2%と仮定し、ランダムウォークさせる)
        total_value = 0
        portfolio_vols = []
        
        for _, row in pdf.iterrows():
            ticker = row['ticker']
            qty = row['quantity']
            curr_price = db[db['ticker'] == ticker]['price'].iloc[0]
            value = curr_price * qty
            total_value += value
            # 簡略化されたボラティリティ推定
            portfolio_vols.append(value)

        # モンテカルロ・エンジン
        # 日次リターンを平均0, 標準偏差2%（暴落時は5%）の正規分布でシミュレート
        results = []
        for _ in range(n_sims):
            # 5日間の累積リターン
            # 暴落シナリオを10%の確率で混ぜる
            is_crash = np.random.rand() < 0.1
            std = 0.05 if is_crash else 0.02
            returns = np.random.normal(0, std, days)
            final_pnl = np.prod(1 + returns) - 1
            results.append(final_pnl)

        results = np.array(results)
        var_95 = np.percentile(results, 5) # 95%信頼区間での損失
        
        survival_rate = (results > -0.10).mean() * 100 # 10%以上の損失を防げる確率

        return {
            "total_value": int(total_value),
            "var_95_pct": round(var_95 * 100, 2),
            "potential_loss": int(total_value * abs(var_95)),
            "survival_rate": round(survival_rate, 1),
            "status": "Safe" if survival_rate > 90 else "Caution" if survival_rate > 70 else "Danger"
        }

if __name__ == "__main__":
    tester = StressTester()
    res = tester.run_simulation()
    print(f"Stress Test Result: {res}")
