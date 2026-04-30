import os
import pandas as pd
import subprocess
import time
import shutil
import joblib

# --- 🧬 Sniper AI V7.1: Safe Evolution Engine ---
# 役割: 統計的安定性を確保し、ロールバック可能な自律進化を実現する。

class SafeEvolveEngine:
    def __init__(self, ic_threshold=0.01, min_trades=30):
        self.ic_threshold = ic_threshold 
        self.min_trades = min_trades    
        self.model_dir = "models"
        self.current_model = "sniper_v4_clf_calibrated.pkl"

    def check_and_evolve(self):
        print("🧬 Monitoring Alpha Health (Safe Mode)...")
        
        if not os.path.exists("trade_log.csv"):
            print("Log empty. Evolution postponed.")
            return

        df = pd.read_csv("trade_log.csv")
        if len(df) < self.min_trades:
            print(f"Insufficient samples (n={len(df)}/{self.min_trades}). Still gathering market evidence...")
            return

        # 1. 移動平均ICの算出 (直近20トレードの窓でノイズを平滑化)
        # 単発の負けに反応せず、継続的な劣化のみを検知する
        df['rolling_ic'] = df['entry_ev'].rolling(20).corr(df['pnl_rate'])
        current_ic = df['rolling_ic'].iloc[-1]
        
        print(f"Current Rolling IC (n=20): {current_ic:.3f}")

        # 2. 進化判定
        if pd.isna(current_ic) or current_ic < self.ic_threshold:
            print("⚠️ SUSTAINED ALPHA DECAY DETECTED. Starting Safe Evolution...")
            self.execute_safe_retrain(current_ic)
        else:
            print(f"✅ Alpha is healthy. Efficiency confirmed.")

    def execute_safe_retrain(self, ic_value):
        """
        現在の知能を保護した上で、新しい知能を生成する
        """
        timestamp = time.strftime("%Y%m%d_%H%M")
        backup_name = f"model_v4_backup_{timestamp}_ic{int(ic_value*1000)}.pkl"
        
        try:
            # --- 手順1: 現行モデルのバックアップ (ロールバック保険) ---
            if os.path.exists(self.current_model):
                shutil.copy(self.current_model, os.path.join(self.model_dir, backup_name))
                print(f"Snapshot saved: {backup_name}")

            # --- 手順2: 再学習 ---
            print("Training Next-Gen Shadow Model...")
            subprocess.run(["python", "ml_train.py"], check=True)
            
            # 再学習で生成されたモデルをシャドー用として保存
            if os.path.exists(self.current_model):
                shutil.move(self.current_model, "shadow_model.pkl")
                print("Shadow model is now in testing phase.")

            # --- 手順3: 成績比較 (Promotion Check) ---
            self.check_for_promotion()
            
            print("🚀 SAFE EVOLUTION COMPLETE. System restored with fresh alpha.")
            
        except Exception as e:
            print(f"❌ Evolution Blocked by System Error: {e}")

    def check_for_promotion(self):
        """シャドー・モデルの成績を分析し、昇格させるか判定"""
        if not os.path.exists("trade_log.csv") or not os.path.exists("shadow_model.pkl"):
            return

        df = pd.read_csv("trade_log.csv")
        if 'is_shadow' not in df.columns: return

        shadow_logs = df[df['is_shadow'] == True]
        live_logs = df[df['is_shadow'] == False]

        if len(shadow_logs) < 10:
            print(f"Shadow model testing... ({len(shadow_logs)}/10 trades)")
            return

        shadow_ic = shadow_logs['entry_ev'].corr(shadow_logs['pnl_rate'], method='spearman')
        live_ic = live_logs['entry_ev'].corr(live_logs['pnl_rate'], method='spearman')

        print(f"Promotion Race: Live IC({live_ic:.3f}) vs Shadow IC({shadow_ic:.3f})")

        if shadow_ic > live_ic + 0.02:
            print("🏆 SHADOW MODEL PROMOTED TO LIVE!")
            shutil.copy("shadow_model.pkl", self.current_model)
            shutil.move("trade_log.csv", f"trade_log_promoted_{int(time.time())}.csv")

if __name__ == "__main__":
    engine = SafeEvolveEngine()
    engine.check_and_evolve()
