import os
import json
import glob
from core import setup_terminal

def restore():
    setup_terminal()
    history = glob.glob("weight_history/weights_*.json")
    if not history:
        print("❌ No backups found in 'weight_history/'.")
        return

    history.sort(reverse=True)
    
    print("📜 Weight History Found:")
    for i, path in enumerate(history):
        print(f"[{i}] {os.path.basename(path)}")
    
    choice = input("\nどの知能を復元しますか？（番号を入力、中止は Enter）: ")
    if not choice: return

    try:
        selected = history[int(choice)]
        with open(selected, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        with open("model_weights.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            
        print(f"✅ Restored weights from: {selected}")
        print("🎯 指令室をリフレッシュ（再スキャン）して新しい知能を適用してください！なのだ！🥇🦾✨")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    restore()
