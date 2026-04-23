import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import io

# --- 🚀 20年間の真実：エリート・スナイパー 20カ年計画 ---
# 司令官、20年分の全データを洗います。
# 2004年〜2024年（リーマンショック、アベノミクス、コロナ全部！）

INVESTMENT = 5000
# 検証時間の短縮のため、有力な50銘柄を選定
TICKERS = [
    "7203.T", "6758.T", "9984.T", "8035.T", "4063.T", "6501.T", "8001.T", "8306.T", "9432.T", "7974.T",
    "9983.T", "9101.T", "4502.T", "6954.T", "6702.T", "7267.T", "8058.T", "8316.T", "4568.T", "6902.T",
    "6723.T", "6503.T", "6752.T", "6857.T", "6981.T", "7741.T", "7733.T", "4911.T", "2502.T", "1605.T",
    "8031.T", "8801.T", "9020.T", "9501.T", "6301.T", "1925.T", "1801.T", "3402.T", "4503.T", "5401.T",
    "6367.T", "7011.T", "8267.T", "8604.T", "9201.T", "9503.T", "9613.T", "9735.T", "2802.T", "3382.T"
]

def get_rsi(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    return 100 - (100 / (1 + (gain / (loss + 1e-9))))

def run_20y_backtest():
    all_data = []
    
    # 20年分の株価と日経平均を一括で取得
    start_year = 2004
    end_year = 2024
    
    print(f"Downloading histories for {len(TICKERS)} tickers (2004-2024)...")
    
    # 日経平均を取得して年度ごとの「地合い」を判定
    n225 = yf.download("^N225", start="2003-01-01", end=f"{end_year+1}-01-31", progress=False)['Close']
    if isinstance(n225, pd.DataFrame): n225 = n225.iloc[:, 0]
    
    # 銘柄ごとにスキャン
    for t in TICKERS:
        try:
            df = yf.download(t, start="2003-01-01", end=f"{end_year+1}-01-31", progress=False)
            if df.empty or len(df) < 500: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['RSI'] = get_rsi(df)
            df['MA25'] = df['Close'].rolling(25).mean()
            df['Slope'] = df['MA25'].diff(5)
            
            pos = None
            for i in range(25, len(df)):
                date = df.index[i]
                year = date.year
                if year < start_year or year > end_year: continue
                
                curr = df['Close'].iloc[i]
                
                if pos is None:
                    if df['RSI'].iloc[i] < 30 and df['Slope'].iloc[i] > -curr * 0.005:
                        pos = {"entry": curr, "date": date, "year": year}
                else:
                    diff = (curr / pos['entry']) - 1
                    days = (date - pos['date']).days
                    if diff >= 0.05 or diff <= -0.03 or days > 15:
                        all_data.append({"year": pos['year'], "profit": diff * INVESTMENT})
                        pos = None
        except Exception as e:
            # print(f"Error {t}: {e}")
            continue
            
    df_res = pd.DataFrame(all_data)
    
    summary = []
    for year in range(start_year, end_year + 1):
        year_trades = df_res[df_res['year'] == year]
        
        # 日経平均の騰落率を算出
        try:
            y_start = n225[n225.index.year == year].iloc[0]
            y_end = n225[n225.index.year == year].iloc[-1]
            n225_pct = (y_end / y_start - 1) * 100
        except: n225_pct = 0
        
        market_type = "BULL" if n225_pct > 10 else "BEAR" if n225_pct < -10 else "FLAT"
        
        if len(year_trades) > 0:
            summary.append({
                "Year": year,
                "Trades": len(year_trades),
                "Win Rate": (year_trades['profit'] > 0).mean() * 100,
                "Total Profit": year_trades['profit'].sum(),
                "N225 %": n225_pct,
                "Market": market_type
            })
            
    return pd.DataFrame(summary)

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("Running Ultimate 20-Year Chronological Backtest...\n")
    report = run_20y_backtest()
    
    # 420銘柄換算 (420/50 = 8.4倍)
    SCALE = 420 / 50
    report['Total Profit'] = (report['Total Profit'] * SCALE).round()
    report['Trades'] = (report['Trades'] * SCALE).round().astype(int)

    print("\n" + "="*85)
    print("💎 THE 20-YEAR TRUTH TABLE (SCALED TO 420 TICKERS)")
    print("="*85)
    print(report.to_string(index=False))
    print("="*85)
    
    # 勝ち越し年・負け越し年をカウント
    wins = len(report[report['Total Profit'] > 0])
    losses = len(report[report['Total Profit'] <= 0])
    print(f"Years Profitable: {wins} | Years Unprofitable: {losses}")

if __name__ == "__main__":
    main()
