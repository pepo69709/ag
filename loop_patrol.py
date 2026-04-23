import time
import subprocess
import sys
import os

def main():
    print("🚁 AI Patrol Initiated. Scanning every 60 seconds...")
    print("Close this window to stop scanning.")
    
    while True:
        try:
            print(f"[{time.strftime('%H:%M:%S')}] Pushing latest reconnaissance data...")
            # bot.pyを実行
            subprocess.run([sys.executable, "bot.py"], check=True)
            print("✅ Scan Complete. Dashboard updated. Waiting 60s...")
        except Exception as e:
            print(f"❌ Scan failed: {e}")
        
        time.sleep(60)

if __name__ == "__main__":
    main()
