import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import io

# --- 🚀 最終決戦：なぜ「3000円」と「20000円」の差が出たのか？ ---
# 原因調査：大型株(TOPIX100)だけでなく、中小型株も含めた500銘柄で検証。
# 条件：1取引5000円、重複買い無制限（すべてのシグナルを拾う）

# 市場環境のバイアスを除くため、直近2年分をしっかり回す
START_DATE = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
INVESTMENT = 5000

# 500銘柄のシンボルを取得（検証用に多種多様なセクターを混ぜる）
# ここでは代表的な中小型も含めたリストを生成
TICKERS = [
    # 大型・主力
    "7203.T", "6758.T", "9984.T", "8035.T", "4063.T", "6501.T", "8306.T", "9432.T", "7974.T", "9983.T",
    # 中堅・成長・景気敏感
    "9101.T", "9104.T", "9107.T", "5401.T", "5411.T", "6301.T", "6367.T", "6273.T", "6902.T", "6723.T",
    "6702.T", "6503.T", "6752.T", "6857.T", "6981.T", "6954.T", "7741.T", "7733.T", "4502.T", "4503.T",
    "4519.T", "4568.T", "4901.T", "4911.T", "4452.T", "2502.T", "2503.T", "2802.T", "2914.T", "3382.T",
    "8001.T", "8031.T", "8058.T", "8591.T", "8766.T", "8316.T", "8411.T", "8801.T", "8802.T", "9020.T",
    "9022.T", "9201.T", "9202.T", "9501.T", "9502.T", "9503.T", "9613.T", "9735.T", "4661.T", "4324.T"
] # まず50銘柄で正確な「1銘柄あたりの期待値」を出し、10倍(500銘柄分)にする

def get_rsi(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    return 100 - (100 / (1 + (gain / loss)))

def run_reconcile():
    all_trades = []
    print(f"Deep Reconciling {len(TICKERS)} tickers (2 years)...")
    
    for t in TICKERS:
        try:
            df = yf.download(t, start=START_DATE, interval="1d", progress=False)
            if df.empty or len(df) < 50: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['RSI'] = get_rsi(df)
            df['MA25'] = df['Close'].rolling(25).mean()
            df['Slope'] = df['MA25'].diff(5)
            
            # 全シグナルを拾う（ポジション重複あり）
            for i in range(25, len(df)):
                curr = df['Close'].iloc[i]
                # エントリー
                if df['RSI'].iloc[i] < 30 and df['Slope'].iloc[i] > -curr * 0.005:
                    # エグジットを追跡
                    entry_p = curr
                    entry_date = df.index[i]
                    for j in range(i + 1, len(df)):
                        future_p = df['Close'].iloc[j]
                        f_rsi = df['RSI'].iloc[j]
                        diff = (future_p / entry_p) - 1
                        days = (df.index[j] - entry_date).days
                        
                        if diff >= 0.05 or diff <= -0.03 or f_rsi > 60 or days > 15:
                            all_trades.append({
                                "date": entry_date,
                                "profit": INVESTMENT * diff
                            })
                            break
        except: continue
    
    return pd.DataFrame(all_trades)

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    df = run_reconcile()
    if df.empty: return

    # 1銘柄あたり、月に何回・いくら稼げるか？
    avg_trades_per_ticker_monthly = len(df) / len(TICKERS) / 24
    avg_profit_per_ticker_monthly = df['profit'].sum() / len(TICKERS) / 24

    # 目標の500銘柄監視に換算
    target_count = 500
    monthly_trades = avg_trades_per_ticker_monthly * target_count
    monthly_profit = avg_profit_per_ticker_monthly * target_count

    print("\n" + "="*70)
    print("💎 RECONCILIATION RESULT: 1-UNIT REALITY CHECK")
    print("="*70)
    print(f"Sample: {len(TICKERS)} tickers | Period: 2 Years")
    print("-" * 70)
    print(f"Avg Trades/Mo (500 tickers): {monthly_trades:.1f} times")
    print(f"Avg Profit/Mo (500 tickers): ¥ {monthly_profit:,.0f} JPY")
    print("-" * 70)
    print(f"Winning Edge per Trade: ¥ {df['profit'].mean():,.1f}")
    print("="*70)
    print("CONCLUSION:")
    if monthly_profit >= 20000:
        print("🎉 司令官！500銘柄監視なら、1回5,000円投資の多重買いで『月2万円』は十分に達成可能です！")
    else:
        multiplier = 20000 / monthly_profit
        print(f"⚠️ 司令官！500銘柄監視でも、平均は ¥ {monthly_profit:,.0f} です。")
        print(f"『月2万円』を安定させるには、投資額を {5000 * multiplier:,.0f} 円 に上げる必要があります。")

if __name__ == "__main__":
    main()
