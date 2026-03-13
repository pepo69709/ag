import time
from dashboard_generator import generate_dashboard
from datetime import datetime

print("==========================================")
print("🚀 AI LIVE PATROL ENGINE STARTING...")
print("==========================================")
print("※ このウィンドウを開いている間、1分おきにダッシュボードを更新します。")
print("※ ブラウザで dashboard.html を開いておけば自動でリフレッシュされます。")

while True:
    try:
        generate_dashboard()
        # 1分待機
        time.sleep(60)
    except KeyboardInterrupt:
        print("\n👋 ライブパトロールを終了します。")
        break
    except Exception as e:
        print(f"⚠️ エラーが発生しました: {e}")
        time.sleep(10) # エラー時は少し待って再試行
