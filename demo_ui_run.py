import time
import random

def demo_live_ui():
    print("🚀 【SNIPER AI】デモ実行モードを起動します...")
    time.sleep(1)
    
    print("\n🌅 [08:55] モーニング・スキャン中...")
    time.sleep(2)
    print("🎯 ターゲット捕捉: 7733.T (オリンパス)")
    print("📊 数学確信度: 91.5%")
    print("📢 Discord通知送信: 『本日の獲物はオリンパスなのだ！』")
    
    time.sleep(2)
    print("\n🔔 [09:00] 寄り付き。監視を開始するのだ！")
    entry_price = 2500.0
    print(f"💰 始値: {entry_price}円")
    
    # シミュレーション：株価が上がっていく様子
    prices = [2505, 2512, 2520, 2524, 2525.5] # 2525以上で+1.0%
    for p in prices:
        diff = ((p / entry_price) - 1) * 100
        print(f"🕵️ パトロール中... 現在値: {p}円 ({diff:+.2f}%)")
        time.sleep(1.5)
        
    print("\n✨ 🎊 ✨ 🎊 ✨ 🎊 ✨ 🎊 ✨")
    print("🏆 【利確】+1.0% 達成なのだ！！！")
    print("🥇 ダッシュボードを『金色』に染めたのだ！")
    print("📢 通知送信: 『勝利！オリンパスを仕留めたのだ！』")
    print("✨ 🎊 ✨ 🎊 ✨ 🎊 ✨ 🎊 ✨")
    
    time.sleep(2)
    print("\n🛡️ 次の事例: 損切りのシミュレーション（守りの美学）")
    entry_price_2 = 1800.0
    print(f"🚀 6758.T (ソニーG) 寄り付き: {entry_price_2}円")
    
    bad_prices = [1795, 1788, 1775, 1763] # 1764以下で-2.0%
    for p in bad_prices:
        diff = ((p / entry_price_2) - 1) * 100
        print(f"⚠️ 警戒中... 現在値: {p}円 ({diff:+.2f}%)")
        time.sleep(1.5)
        
    print("\n💜 🛡️ 💜 🛡️ 💜 🛡️ 💜 🛡️ 💜")
    print("⚠️ 【撤退】損切ライン(-2.0%) 到達。")
    print("👾 ダッシュボードを『黒紫』にして戦線を離脱するのだ。")
    print("📢 通知送信: 『撤退。ここは勇気ある転進なのだ。』")
    print("💜 🛡️ 💜 🛡️ 💜 🛡️ 💜 🛡️ 💜")
    
    print("\n🏁 デモ終了。本番ではこれが3分〜5分おきに自動で行われます。")

if __name__ == "__main__":
    demo_live_ui()
