import pandas as pd
import numpy as np
import os

# --- 🧪 Sniper AI V6.3: IC Validator ---
# 役割: 実戦ログ(trade_log.csv)を分析し、予測EVと実際の結果の相関(IC)を算出する。

def validate_ic(log_file="trade_log.csv"):
    if not os.path.exists(log_file):
        print("No trade log found. Start trading to accumulate data!")
        return

    df = pd.read_csv(log_file)
    if len(df) < 5:
        print(f"Not enough data (n={len(df)}). Need at least 10-20 trades for valid IC.")
        return

    # 情報係数 (IC) = 予測EVと実際のPnLの相関
    # スピアマンの順位相関を用いるのがクオンツの標準
    ic = df['entry_ev'].corr(df['pnl_rate'], method='spearman')
    
    # ヒット率
    hit_rate = (df['pnl_rate'] > 0).mean()

    print(f"--- Sniper AI Intelligence Report ---")
    print(f"Sample Size   : {len(df)} trades")
    print(f"Information Coeff (IC) : {ic:.3f}")
    print(f"Hit Rate      : {hit_rate*100:.1f}%")
    print(f"Avg PnL per Trade      : {df['pnl_rate'].mean():.2f}%")
    print(f"------------------------------------")
    
    if ic > 0.05:
        print("✅ Alpha detected! The model is capturing market structural edges.")
    elif ic > 0:
        print("⚠️ Weak edge. Consider refining features or exit strategy.")
    else:
        print("❌ No edge detected. The model is currently noise-driven.")

if __name__ == "__main__":
    validate_ic()
