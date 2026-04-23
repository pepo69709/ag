import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import io

# --- 🚀 超・インテリジェンス検証: ハースト指数 (Hurst Exponent) による「位相」判定 ---
# $H < 0.5$: 逆張りチャンス（平均回帰）
# $H > 0.5$: 順張りチャンス（トレンド継続）

TICKERS = ["7203.T", "6758.T", "9984.T", "8035.T", "4063.T", "6501.T", "7733.T"]

START_DATE = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')

def get_hurst_exponent(time_series, max_lag=20):
    """
    ハースト指数を計算し、市場の「性質（位相）」を判定する。
    """
    lags = range(2, max_lag)
    tau = [np.sqrt(np.std(np.subtract(time_series[lag:], time_series[:-lag]))) for lag in lags]
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    return poly[0] * 2.0

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def backtest_hurst_sniper(ticker):
    try:
        df = yf.download(ticker, start=START_DATE, interval="1d", progress=False)
        if df.empty or len(df) < 50: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df['RSI'] = calculate_rsi(df['Close'])
        
        trades = []
        position = False
        entry_price = 0
        entry_date = None

        # 20日間のデータを使ってハースト指数を常に計算
        for i in range(30, len(df)):
            window_data = df['Close'].iloc[i-25:i].values
            h = get_hurst_exponent(window_data)
            
            curr_price = df['Close'].iloc[i]
            rsi = df['RSI'].iloc[i]
            
            # --- エントリーロジック ---
            # H < 0.45 かつ RSI < 30 : 「そろそろ戻る」と確信できる逆張り
            # H > 0.55 かつ 移動平均突破 : 「ここから伸びる」と確信できる順張り
            
            entry_signal = False
            strat_type = ""
            
            if h < 0.45 and rsi < 30:
                entry_signal = True
                strat_type = "Mean Reversion (H<0.45)"
            elif h > 0.55 and rsi > 50: # RSI 50突破で順張り
                entry_signal = True
                strat_type = "Trend Following (H>0.55)"
            
            if not position and entry_signal:
                position = True
                entry_price = curr_price
                entry_date = df.index[i]
                start_strat = strat_type
            elif position:
                profit_pct = (curr_price / entry_price) - 1
                hold_days = (df.index[i] - entry_date).days
                
                # 利益確定・損切り
                if profit_pct >= 0.05 or profit_pct <= -0.03 or hold_days > 15:
                    trades.append({"type": start_strat, "profit": profit_pct * 100})
                    position = False
        return trades
    except: return None

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    results = []
    print(f"Running Advanced 'Hurst Phase' Analysis for {len(TICKERS)} tickers...")
    for t in TICKERS:
        res = backtest_hurst_sniper(t)
        if res: results.extend(res)
    
    df = pd.DataFrame(results)
    if df.empty: return

    report = df.groupby('type')['profit'].agg(['count', 'mean', lambda x: (x > 0).mean() * 100]).reset_index()
    report.columns = ['Strategy Type', 'Trades', 'Avg Profit%', 'Win Rate%']

    print("\n" + "="*60)
    print("ELITE SNIPER: PHASE-BASED STRATEGY PERFORMANCE")
    print("="*60)
    print(report.to_string(index=False))
    print("="*60)
    print("INSIGHT: ハースト指数で市場の『位相』を見抜けば、逆張りと順張りを自動で使い分けられるのだ！")

if __name__ == "__main__":
    main()
