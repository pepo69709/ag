import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import io

# --- ⚙️ スイング・バックテスト設定 (スケール検証) ---
TICKERS = [
    "7733.T", "7203.T", "9984.T", "6758.T", "8035.T", "6501.T", "4063.T",
    "6723.T", "6920.T", "6857.T", "6902.T", "6981.T", "6762.T", "6503.T",
    "6367.T", "6273.T", "6113.T", "6146.T", "7011.T", "7012.T", "7013.T",
    "4502.T", "4503.T", "4519.T", "4523.T", "4568.T", "4578.T", "4452.T",
    "4901.T", "4911.T", "2502.T", "2503.T", "2802.T", "2914.T", "3382.T"
] # 35銘柄に拡大
# スイングなので期間を長めに (2年間)
START_DATE = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
END_DATE = datetime.now().strftime('%Y-%m-%d')

FEE = 0.000 # 楽天証券 0円

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def backtest_swing_rsi(ticker):
    print(f"Analyzing {ticker} (Swing RSI)...")
    df = yf.download(ticker, start=START_DATE, interval="1d")
    if df.empty: return None

    # yfinanceのマルチインデックス対策
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # インジケーター計算
    df['RSI'] = calculate_rsi(df['Close'])
    
    position = False
    entry_price = 0
    entry_date = None
    trades = []

    for i in range(1, len(df)):
        current_price = df['Close'].iloc[i]
        rsi = df['RSI'].iloc[i]
        
        # エントリー条件: RSI < 30 (売られすぎ)
        if not position and rsi < 30:
            position = True
            entry_price = current_price
            entry_date = df.index[i]
        
        # エグジット条件: +5%利確 or RSI > 60 or 10日経過
        elif position:
            profit_pct = (current_price / entry_price) - 1
            hold_days = (df.index[i] - entry_date).days
            
            if profit_pct >= 0.05 or rsi > 60 or hold_days > 10:
                # 往復の手数料を引く
                net_profit = profit_pct - (FEE * 2)
                trades.append({
                    "ticker": ticker,
                    "entry_date": entry_date,
                    "exit_date": df.index[i],
                    "raw_profit": profit_pct * 100,
                    "net_profit": net_profit * 100,
                    "hold_days": hold_days
                })
                position = False

    return pd.DataFrame(trades)

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("--- Swing Strategy Validation: RSI Oversold Model ---")
    
    all_trades = []
    for t in TICKERS:
        res = backtest_swing_rsi(t)
        if res is not None and not res.empty:
            all_trades.append(res)
    
    if not all_trades:
        print("No trades executed with this logic.")
        return

    final_df = pd.concat(all_trades)
    # 日付順にソート (複利計算・同時発生の把握のため)
    final_df = final_df.sort_values('entry_date')
    
    # --- パターンA: 毎回5000円投資 (軍資金が潤沢にある場合) ---
    INVEST_FIXED = 5000
    final_df['profit_fixed_yen'] = (final_df['net_profit'] / 100) * INVEST_FIXED
    total_profit_fixed = final_df['profit_fixed_yen'].sum()
    
    # --- パターンB: 最初に5000円だけ持っている (複利) ---
    # ※株の単元などは無視し、資金の増減率だけを追う
    capital_cumulative = 5000
    for idx, row in final_df.iterrows():
        # net_profit は % 単位なので 100 で割る
        capital_cumulative *= (1 + (row['net_profit'] / 100))
    total_profit_cumulative = capital_cumulative - 5000

    # 取引頻度 (過去2年 = 約480営業日)
    total_days = (datetime.strptime(END_DATE, '%Y-%m-%d') - datetime.strptime(START_DATE, '%Y-%m-%d')).days
    business_days = total_days * (5/7) # 簡易的な営業日
    trades_per_day = len(final_df) / business_days

    # 同時保有のチェック (ある日に何銘柄持っているか)
    # 簡易版：エントリー日でカウント
    max_concurrent = final_df.groupby('entry_date').size().max()

    summary = {
        "Total Trades": len(final_df),
        "Win Rate (%)": (len(final_df[final_df['net_profit'] > 0]) / len(final_df)) * 100,
        "Pattern A: Fixed 5k/trade": total_profit_fixed,
        "Pattern B: Start with 5k (Compound)": total_profit_cumulative,
        "Avg Trades per Day": trades_per_day,
        "Max Concurrent Entry": max_concurrent
    }

    print("\n" + "="*40)
    print("SIMULATION: Rakuten 0% Fee")
    print("="*40)
    for k, v in summary.items():
        if "Fixed" in k or "Compound" in k:
            print(f"{k:35}: +{v:,.0f} JPY")
        elif "Trades" in k:
            print(f"{k:35}: {v:.3f}")
        elif "Concurrent" in k or "Total" in k:
            print(f"{k:35}: {v}")
        else:
            print(f"{k:35}: {v:.2f}%")
    print("="*40)
    
    print("\nINSIGHT: 2つの計算結果を出しました！")
    print(f"・毎回5,000円投資(A): 2年で利益は合計 {total_profit_fixed:,.0f} 円。")
    print(f"・5,000円を転がし続けた(B): 2年で利益は合計 {total_profit_cumulative:,.0f} 円。")
    print(f"\n一度に最大で {max_concurrent} 銘柄の買い注文が出る可能性があります。")

if __name__ == "__main__":
    main()
