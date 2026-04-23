import yfinance as yf
import pandas as pd
import json
import glob
import os
from core import TICKER_LIST, get_indicators, calculate_score, setup_terminal

# --- 🏹 Sniper AI: Performance Auditor ---
# 「どの知能が今一番稼げるか？」を過去30日の本物データでガチンコ対決させる審判プログラム。

def backtest_weights(training_data, weights, regime):
    """特定の重みセットで直近のシミュレーションを行い、合計利益率を返す"""
    total_profit = 0
    for ticker, df in training_data.items():
        # 直近10日間でテスト
        for i in range(len(df) - 10, len(df) - 1):
            row = df.iloc[i]
            score = calculate_score(ticker, row, weights, regime)
            
            if score >= 70:
                buy_price = df.iloc[i+1]['Open']
                sell_price = df.iloc[i+1]['Close']
                total_profit += (sell_price / buy_price) - 1
                
    return total_profit

def audit():
    setup_terminal()
    print("⚖️ Sniper AI: Objective Performance Audit starting...")
    
    # 1. バックアップと現在の重みをすべて取得
    weight_files = glob.glob("weight_history/weights_*.json")
    if os.path.exists("model_weights.json"):
        weight_files.append("model_weights.json")
    
    if not weight_files:
        print("❌ No weights found to compare.")
        return

    # 2. 最新データの取得 (主要20銘柄、直近30日)
    print("📡 Fetching latest 30-day market data for audit...")
    test_data = {}
    for ticker in TICKER_LIST[:20]:
        try:
            df = yf.download(ticker, period="1mo", progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            test_data[ticker] = get_indicators(df)
        except: continue

    results = []
    
    # 3. 各重みセットの性能を測定 (現在はBULLレジームを想定)
    for path in weight_files:
        label = "CURRENT" if "model_weights.json" in path else os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                weights = json.load(f)
            
            perf = backtest_weights(test_data, weights["regime_bull"], "BULL")
            results.append({"label": label, "profit": perf})
        except: continue

    # 4. ランキング表示
    results.sort(key=lambda x: x["profit"], reverse=True)
    
    print("\n🏆 --- PERFORMANCE LEADERBOARD (Last 30 Days) ---")
    for i, res in enumerate(results):
        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "  "
        print(f"{medal} Rank {i+1}: {res['label']} -> Yield: {res['profit']*100:+.2f}%")

    print("\n💡 結論: 最も高い%を出している重みが、今の市場に最も適した『旬な知能』です！なのだ！🥇🦾✨")

if __name__ == "__main__":
    audit()
