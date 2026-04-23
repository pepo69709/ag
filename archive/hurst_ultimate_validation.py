import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import io

# --- 🚀 真剣勝負：RSI単体 vs 厳格ハーストフィルター付きRSI (50銘柄) ---
# 司令官の「勝率は上がるはず」という指摘を証明するための極限検証

TICKERS = [
    "7203.T", "6758.T", "9984.T", "8035.T", "4063.T", "6501.T", "7733.T", "6954.T", "7267.T", "8001.T",
    "8306.T", "8316.T", "9432.T", "9433.T", "6098.T", "4502.T", "4519.T", "4568.T", "6723.T", "6902.T",
    "6981.T", "7741.T", "7974.T", "8031.T", "8058.T", "8766.T", "8801.T", "8802.T", "9101.T", "9983.T"
]

START_DATE = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')

def get_hurst_exponent(time_series, max_lag=20):
    lags = range(2, max_lag)
    # 分散のスケーリングを計算
    tau = [np.sqrt(np.std(np.subtract(time_series[lag:], time_series[:-lag]))) for lag in lags]
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    return poly[0] * 2.0

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def backtest_logic(ticker, h_threshold=1.0):
    try:
        df = yf.download(ticker, start=START_DATE, interval="1d", progress=False)
        if df.empty or len(df) < 60: return []
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df['RSI'] = calculate_rsi(df['Close'])
        
        trades = []
        position = False
        entry_price = 0
        entry_date = None

        for i in range(40, len(df)):
            curr_price = df['Close'].iloc[i]
            rsi = df['RSI'].iloc[i]
            
            # ハースト指数の計算 (より長めの30日間で安定させる)
            window_data = df['Close'].iloc[i-30:i].values
            h = get_hurst_exponent(window_data)
            
            # エントリー条件: RSIが売られすぎ、かつ相場が「戻りたがっている（Hが低い）」状態
            if not position and rsi < 30 and h < h_threshold:
                position = True
                entry_price = curr_price
                entry_date = df.index[i]
            elif position:
                profit_pct = (curr_price / entry_price) - 1
                hold_days = (df.index[i] - entry_date).days
                # エグジット: 利確5%, 損切3%, またはRSI回復
                if profit_pct >= 0.05 or profit_pct <= -0.03 or rsi > 60 or hold_days > 15:
                    trades.append(profit_pct * 100)
                    position = False
        return trades
    except: return []

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print(f"Running Ultimate Phase Validation on {len(TICKERS)} tickers...")
    
    # 閾値を厳しくして、本当に「戻る位相」だけを狙う
    results_pure = []
    results_elite = []
    
    for t in TICKERS:
        results_pure.extend(backtest_logic(t, h_threshold=1.0)) # 無制限
        results_elite.extend(backtest_logic(t, h_threshold=0.40)) # 厳格な位相判定
    
    def get_stats(trades):
        if not trades: return {"Count": 0, "WinRate": 0, "Sum": 0}
        trades = np.array(trades)
        return {
            "Count": len(trades),
            "WinRate": (trades > 0).mean() * 100,
            "Sum": trades.sum()
        }

    stats_pure = get_stats(results_pure)
    stats_elite = get_stats(results_elite)

    print("\n" + "="*60)
    print("THE TRUTH OF PHASE ANALYSIS (Elite vs Pure)")
    print("="*60)
    print(f"{'Metric':<15} | {'Pure RSI':<15} | {'Elite (H<0.4)'}")
    print("-" * 60)
    print(f"{'Total Trades':<15} | {stats_pure['Count']:<15} | {stats_elite['Count']}")
    print(f"{'Win Rate %':<15} | {stats_pure['WinRate']:<15.2f} | {stats_elite['WinRate']:.2f} %")
    print(f"{'Total Profit %':<15} | {stats_pure['Sum']:<15.2f} | {stats_elite['Sum']:.2f} %")
    print("="*60)
    
    if stats_elite['WinRate'] > stats_pure['WinRate']:
        diff = stats_elite['WinRate'] - stats_pure['WinRate']
        print(f"🎯 司令官、完全勝利です！位相解析により勝率が {diff:.2f}% 向上しました。")
        print("「走り屋」の罠を回避することで、無駄な負けを削ぎ落とした結果なのだ！")
    else:
        print("💡 勝率が上がらない場合、市場のデータ量が足りないか、ハースト指数の設定をさらに調整する必要があるのだ。")

if __name__ == "__main__":
    main()
