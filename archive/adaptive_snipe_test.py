import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import io

# --- 🚀 次世代「アダプティブ・スナイパー」：市場環境に合わせた重み付けの変化 ---
# 1. ボラティリティに応じた利確幅 (ATR)
# 2. 地合いに応じたエントリー厳格化 (日経225)

START_DATE = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
TICKERS = ["7203.T", "6758.T", "9984.T", "8035.T", "4063.T"] 

def calculate_atr(df, window=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=window).mean()

def calculate_rsi(data):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    return 100 - (100 / (1 + (gain / loss)))

def adaptive_backtest():
    all_res = []
    
    # 日経平均を取得して「地合い」を判定
    n225 = yf.download("^N225", start=START_DATE, interval="1d", progress=False)['Close']
    if isinstance(n225, pd.DataFrame): n225 = n225.iloc[:, 0]
    n225_ma200 = n225.rolling(200).mean()

    for ticker in TICKERS:
        try:
            df = yf.download(ticker, start=START_DATE, interval="1d", progress=False)
            if df.empty or len(df) < 200: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['RSI'] = calculate_rsi(df['Close'])
            df['ATR'] = calculate_atr(df)
            df['MA25'] = df['Close'].rolling(25).mean()
            df['Slope'] = df['MA25'].diff(5)
            
            pos = None
            for i in range(200, len(df)):
                date = df.index[i]
                curr = df['Close'].iloc[i]
                atr = df['ATR'].iloc[i]
                rsi = df['RSI'].iloc[i]
                
                # 地合い判定: 日経225が200日線より上なら「強気」、下なら「弱気」
                is_bull = n225.loc[:date].iloc[-1] > n225_ma200.loc[:date].iloc[-1]
                
                if pos is None:
                    # エントリー条件の「重み」を変化させる
                    # 強気相場: RSI < 35 でもOK (緩く拾う)
                    # 弱気相場: RSI < 25 じゃないとダメ (厳選する)
                    threshold = 35 if is_bull else 25
                    
                    if rsi < threshold and df['Slope'].iloc[i] > -curr * 0.005:
                        # 利確目標もボラティリティ(ATR)に合わせる
                        # ATRの2倍を狙う (ボラが大きい時は大きく獲り、小さい時はサッと逃げる)
                        target = curr + (atr * 2.0)
                        stop = curr - (atr * 1.5)
                        pos = {"entry": curr, "target": target, "stop": stop, "date": date}
                else:
                    days = (date - pos['date']).days
                    if curr >= pos['target'] or curr <= pos['stop'] or days > 15:
                        p_pct = (curr / pos['entry'] - 1) * 100
                        all_res.append(p_pct)
                        pos = None
        except: continue
    
    return all_res

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("Running 'Adaptive Sniper' (Volatility-Adjusted + Regime-Switching)...")
    results = adaptive_backtest()
    if results:
        res = np.array(results)
        print("\n" + "="*60)
        print("ADAPTIVE STRATEGY RESULT")
        print("="*60)
        print(f"Total Trades: {len(res)}")
        print(f"Win Rate    : {(res > 0).mean() * 100:.2f}%")
        print(f"Avg Profit %: {res.mean():.2f}%")
        print("="*60)
        print("INSIGHT: 『地合いがいい時はチャンスを多く、地合いが悪い時は守りを固める』重み付けの自動変化を搭載成功。なのだ！🥇")

if __name__ == "__main__":
    main()
