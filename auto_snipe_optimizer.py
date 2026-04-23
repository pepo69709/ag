import json
import os
import glob
from core import TICKER_LIST, setup_terminal, load_weights
import train
import compare_performances
import bot

# --- 🏹 Sniper AI: Auto-Optimizer (The Brain) ---
# 「学習 -> 比較 -> 最強を適用 -> スキャン」を全自動で行う統合指令プログラム。

def get_best_weight_file():
    """全バックアップ＋今の重みの中で、直近30日の利益が最高のものを探す"""
    print("\n⚖️ Step 2: Finding the most profitable intelligence...")
    
    # 最新データを1回だけ取得（効率化のため）
    test_data = {}
    import yfinance as yf
    from core import get_indicators
    for ticker in TICKER_LIST[:20]:
        try:
            df = yf.download(ticker, period="1mo", progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            test_data[ticker] = get_indicators(df)
        except: continue

    weight_files = glob.glob("weight_history/weights_*.json")
    if os.path.exists("model_weights.json"):
        weight_files.append("model_weights.json")
    
    best_path = None
    max_profit = -999
    
    import compare_performances as auditor
    import pandas as pd # 念のため
    
    results = []
    for path in weight_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                w = json.load(f)
            
            # メタデータからレジームを取得（なければ判定）
            w_regime = w.get("metadata", {}).get("training_regime", "BULL")
            
            perf = auditor.backtest_weights(test_data, w["regime_bull"], "BULL")
            results.append({"path": path, "profit": perf, "regime": w_regime})
        except: continue
        
    # ベストを探す
    if not results: return None, -999
    
    best = max(results, key=lambda x: x["profit"])
    
    # --- 🏛️ クリーンアップ（殿堂入りシステム） ---
    # 常時シミュレーション対象を「精鋭」だけに絞り込む
    maintain_weights(results)
    
    return best["path"], best["profit"]

def maintain_weights(results):
    """不要な重みファイルを削除し、各レジームの精鋭と直近だけを残す"""
    print("🧹 Maintenance: Purging mediocre intelligence...")
    
    # 保存ルール
    to_keep = set()
    
    # 1. 各レジーム（BULL, BEAR, FLAT, VOLATILE）のTOP 3を殿堂入り
    regimes = ["BULL", "BEAR", "FLAT", "VOLATILE"]
    for r in regimes:
        r_list = [x for x in results if x["regime"] == r]
        r_list.sort(key=lambda x: x["profit"], reverse=True)
        for elite in r_list[:3]:
            to_keep.add(elite["path"])
            
    # 2. 直近の5個は成績に関わらず残す
    results.sort(key=lambda x: os.path.getmtime(x["path"]), reverse=True)
    for recent in results[:5]:
        to_keep.add(recent["path"])
        
    # 3. 司令官が名前を付けたファイルは保護（数字以外の名前が含まれる場合）
    for res in results:
        basename = os.path.basename(res["path"])
        if not basename.replace("weights_", "").replace(".json", "").replace("_", "").isdigit():
            to_keep.add(res["path"])
            
    # 保護対象以外を削除
    for res in results:
        path = res["path"]
        if path not in to_keep and "model_weights.json" not in path:
            try:
                os.remove(path)
                print(f"🗑️ Removed: {os.path.basename(path)}")
            except: pass

def run_pipeline():
    setup_terminal()
    print("🚀 Sniper AI: Full-Auto Pipeline Initiated!")
    
    # 1. 学習 (新しい重み候補を作る)
    print("\n🏋️ Step 1: Training new candidate intelligence...")
    train.train()
    
    # 2. 比較 (最高の知能を選別)
    best_path, profit = get_best_weight_file()
    
    if best_path:
        print(f"\n🏆 The winner is: {os.path.basename(best_path)} with {profit*100:+.2f}% yield!")
        
        # 3. 適用 (最強を model_weights.json に上書き)
        if "model_weights.json" not in best_path:
            print(f"🔄 Automatically applying the best intelligence from history...")
            with open(best_path, "r", encoding="utf-8") as f:
                best_data = json.load(f)
            with open("model_weights.json", "w", encoding="utf-8") as f:
                json.dump(best_data, f, indent=4)
        else:
            print("✨ Current weights are already the best. No restore needed.")
            
        # 4. 最終スキャンの実行
        print("\n🏹 Step 3: Scanning the market with the best intelligence...")
        bot.main()
        
        print("\n🥇 Full-Auto Pipeline Complete! Check your Dashboard! なのだ！🥇🦾✨")
    else:
        print("❌ Pipeline failed: No valid weights found.")

if __name__ == "__main__":
    run_pipeline()
