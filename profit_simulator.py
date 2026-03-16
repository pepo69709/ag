import pandas as pd

# ==========================================
# 💸 リアル期待値シミュレーター (1トレード 5000円 / 手数料 0.5%)
# ==========================================

# 設定値
TRADE_SIZE = 5000    # 1件あたりの投資額 (5000円)
FEE_PERCENT = 0.5    # 往復手数料 (買+売 合計で 0.5%)
PROFIT_TARGET = 1.0  # 利確ターゲット
STOP_LOSS = 2.0      # 損切目安

def simulate_expectancy(name, win_rate, annual_chances, round_trip_fee):
    # 1トレードあたりの損益計算 (round_trip_fee: 買+売の合計手数料)
    net_win = PROFIT_TARGET - round_trip_fee  # 勝ちトレードの利益 (%)
    net_loss = - (STOP_LOSS + round_trip_fee) # 負けトレードの損失 (%)
    
    # 期待値 (%)
    expectancy_pct = (win_rate/100 * net_win) + ((1 - win_rate/100) * net_loss)
    
    # 1トレードあたりの期待利益 (円)
    profit_per_trade = TRADE_SIZE * (expectancy_pct / 100)
    
    # 月間・年間の期待利益
    monthly_chances = annual_chances / 12
    monthly_profit = profit_per_trade * monthly_chances
    annual_profit = profit_per_trade * annual_chances
    
    return {
        "name": name,
        "win_rate": win_rate,
        "expectancy_pct": expectancy_pct,
        "profit_per_trade": profit_per_trade,
        "monthly_profit": monthly_profit,
        "annual_profit": annual_profit
    }

# データの入力
cases = [
    # 日本株：楽天証券「ゼロコース」 (往復手数料 0%)
    simulate_expectancy("🇯🇵 日本株 (楽天 0円・素)", 79.0, 6946, 0.0),
    simulate_expectancy("🇯🇵 日本株 (楽天 0円・AI厳選)", 95.0, 6946 * 0.1, 0.0),
    
    # 仮想通貨：bitbank/GMO等の「板取引・Maker」 (往復手数料 -0.02% = 利益)
    simulate_expectancy("🌐 仮想通貨 (板/指値 -0.02%・素)", 83.7, 606, -0.02),
    simulate_expectancy("🌐 仮想通貨 (板/指値 -0.02%・AI厳選)", 92.0, 606 * 0.3, -0.02)
]

print("="*60)
print(f"💰 究極コスト削減シミュレーション (投資: {TRADE_SIZE}円)")
print("  - 日本株: 楽天証券 0円コース")
print("  - 仮想通貨: 国内取引所 板取引(Maker) -0.01%")
print("="*60)
print(f"{'ケース':<25} | {'勝率':<5} | {'期待利益/回':<10} | {'期待利益/月'}")
print("-" * 60)

for c in cases:
    print(f"{c['name']:<25} | {c['win_rate']:>4.1f}% | {c['profit_per_trade']:>7.1f}円 | {c['monthly_profit']:>7.0f}円")

print("-" * 60)
print("※ 仮想通貨は、取引所（板取引）を使えば手数料を 0.1% 以下に抑えられ、さらに期待値が跳ね上がります。")
