import os
import shutil
import glob

# --- 🔙 Sniper AI V7.1: Rollback Utility ---
# 役割: 劣化した新モデルを捨て、過去の「勝てていた知能」を即座に復元する。

def rollback():
    model_dir = "models"
    backups = glob.glob(os.path.join(model_dir, "*.pkl"))
    
    if not backups:
        print("No backup models found in storage.")
        return

    # 最新のバックアップを表示
    backups.sort(key=os.path.getmtime, reverse=True)
    
    print("--- 💾 Available Restore Points ---")
    for i, b in enumerate(backups[:5]):
        print(f"[{i}] {os.path.basename(b)}")
    
    choice = input("\nSelect version to restore (number) or 'q' to quit: ")
    if choice.isdigit() and int(choice) < len(backups):
        selected_model = backups[int(choice)]
        shutil.copy(selected_model, "sniper_v4_clf_calibrated.pkl")
        print(f"✅ RESTORE COMPLETE: {os.path.basename(selected_model)} is now LIVE.")
    else:
        print("Rollback cancelled.")

if __name__ == "__main__":
    rollback()
