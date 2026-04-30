import pandas as pd
import numpy as np
import os
from tabulate import tabulate

# --------------------------------------------------------------
# evaluate_performance.py
# --------------------------------------------------------------
# V14.0: The Structural Integrity Guard
#   - Robustness Check: Parameter sensitivity
#   - Verdict: Glass vs Iron Strategy
# --------------------------------------------------------------

def diagnosis():
    report_file = "robust_report.csv"
    if not os.path.exists(report_file):
        print(f"Error: {report_file} not found. Run compute_future_return.py first.")
        return

    df = pd.read_csv(report_file)

    print("\n" + "="*80)
    print("🧱 SNIPER AI V14.0: STRUCTURAL INTEGRITY DIAGNOSIS")
    print(" (Parameter Perturbation | Sensitivity Analysis | Glass vs Iron)")
    print("="*80)

    # 1. パフォーマンスの分散（堅牢性）を算出
    # 主要なホライズン（5, 15, 60）ごとに、パラメータを振った時の安定度を見る
    summary = []
    for h_main in [5, 15, 60]:
        # 近接ホライズンを含めたグループ
        h_group = [h_main - 1, h_main, h_main + 1, h_main - 5, h_main + 5]
        sub = df[df["horizon"].isin(h_group)].copy()
        
        if sub.empty: continue
        
        avg_alpha = sub["alpha"].mean()
        std_alpha = sub["alpha"].std()
        avg_sharpe = sub["sharpe"].mean()
        
        # 堅牢性スコア: 平均に対する標準偏差の比率 (低いほど良い)
        cv_alpha = (std_alpha / abs(avg_alpha)) if abs(avg_alpha) > 1e-6 else 1.0
        
        status = "IRON" if cv_alpha < 0.3 and avg_alpha > 0 else "GLASS"
        
        summary.append({
            "Main_Horizon": f"{h_main}m",
            "Avg_Alpha": avg_alpha,
            "Alpha_CV": cv_alpha,
            "Avg_Sharpe": avg_sharpe,
            "Integrity": status
        })

    # 表示
    disp = pd.DataFrame(summary)
    print("\n--- ROBUSTNESS SUMMARY ---")
    print(tabulate(disp, headers="keys", tablefmt="github", showindex=False))

    # 2. 最終宣告 (The Verdict)
    print("\n--- FINAL VERDICT: STRUCTURAL CHECK ---")
    iron_count = (disp["Integrity"] == "IRON").sum()
    
    if iron_count == 0:
        print("### VERDICT: [ REJECT ]")
        print("REASON: Strategy is 'GLASS'. Results depend too much on exact parameters.")
        print("ADVICE: Strategy will likely break in real market conditions.")
    elif iron_count < len(disp):
        print("### VERDICT: [ WATCH ]")
        print(f"REASON: Only {iron_count} horizons are stable. Partial robustness confirmed.")
        print("ADVICE: Paper trade with strict monitoring on parameters.")
    else:
        print("### VERDICT: [ ADOPT ]")
        print("REASON: 'IRON' STRATEGY. Solid edge across all parameter variations.")
        print("ADVICE: High confidence for real deployment.")

    print("\n" + "#"*80)

if __name__ == "__main__":
    diagnosis()
