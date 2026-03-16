import time
import subprocess
import sys
from datetime import datetime
import config

print("==========================================")
print("🛡️ 【AI 自動パトロール：30分おき通知モード】")
print("==========================================")
print("このスクリプトは、30分ごとに全500銘柄をスキャンし、")
print("AIが合格を出した銘柄があれば即座にDiscordへ通知します。")
print("※市場稼働時間外でも実行はされますが、データは更新されません。")

def run_scanner():
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n[🔔 {now}] スキャンを開始します...")
        # scanner.py を別プロセスで実行
        subprocess.run([sys.executable, "scanner.py"], check=True)
        print(f"[✅ {now}] スキャン完了。次の実行まで30分待機します。")
    except Exception as e:
        print(f"⚠️ スキャン実行中にエラーが発生しました: {e}")

if __name__ == "__main__":
    # 初回実行
    run_scanner()
    
    # ループ
    while True:
        try:
            # 30分 = 1800秒
            time.sleep(1800)
            run_scanner()
        except KeyboardInterrupt:
            print("\n👋 自動パトロールを終了します。指示を待機します。")
            break
        except Exception as e:
            print(f"⚠️ 待機中に予期せぬエラーが発生しました: {e}")
            time.sleep(60)
