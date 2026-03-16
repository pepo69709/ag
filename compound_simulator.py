import pandas as pd

# ==========================================
# 📈 雪だるま式・資産倍増シミュレーター (複利の魔法)
# ==========================================

def simulate_compounding(initial_capital=5000, monthly_win_rate=95, trades_per_day=3):
    # 設定
    profit_per_trade_pct = 1.0  # 1トレード 1.0% 利確
    fee_pct = 0.0              # 楽天証券 0円想定
    tax_pct = 20.315           # 利益にかかる税金 (源泉徴収想定)
    
    capital = initial_capital
    history = []
    
    # 毎月の稼働日 (約20日)
    days_per_month = 20
    total_months = 12
    
    print(f"🚀 【複利パワー測定】開始元本: {initial_capital}円 / 1日 {trades_per_day}回取引 / 勝率 {monthly_win_rate}%")
    print("-" * 60)
    print(f"{'経過月':<5} | {'資産合計':<10} | {'その月の利益':<10} | {'倍率'}")
    print("-" * 60)
    
    for month in range(1, total_months + 1):
        start_month_capital = capital
        
        # 1ヶ月の全トレード回数
        total_trades = days_per_month * trades_per_day
        
        for _ in range(total_trades):
            # 勝敗判定 (勝率に基づく期待値計算)
            # 実際には勝ち負けがありますが、ここではシミュレーションとして平均的な期待損益を適用
            # 期待損益 = (勝率 * 1%) + (負率 * -2%)
            expectancy_pct = (monthly_win_rate/100 * profit_per_trade_pct) + ((1 - monthly_win_rate/100) * -2.0)
            
            # 手数料引き
            net_expectancy = expectancy_pct - fee_pct
            
            # 資産への反映
            profit = capital * (net_expectancy / 100)
            capital += profit
            
        # 税金計算 (月末に利益の約20%を引く)
        monthly_profit = capital - start_month_capital
        if monthly_profit > 0:
            tax = monthly_profit * (tax_pct / 100)
            capital -= tax
            
        history.append({
            "month": month,
            "capital": capital,
            "profit": monthly_profit * (1 - tax_pct/100),
            "multiple": capital / initial_capital
        })
        
        print(f"{month:>3}ヶ月目 | {int(capital):>7}円 | {int(monthly_profit * (1 - tax_pct/100)):>8}円 | {capital/initial_capital:>4.2f}倍")

    print("-" * 60)
    print(f"🏁 1年後の結果: {int(capital)}円 (資産が約 {capital/initial_capital:.1f} 倍に！)")
    print("※ 5,000円という小さな種銭も、AIの的中率と複利を組み合わせれば『本物の資産』への階段を登り始めます。")

if __name__ == "__main__":
    simulate_compounding()
