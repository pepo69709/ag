import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import io

# --- 🚀 司令官への詳細報告：なぜ「アダプティブ（動的）」は失敗したのか？ ---
# 15回の取引を1つずつ詳細にログ出しし、失敗のパターンを解析する。

START_DATE = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
TICKERS = ["7203.T", "6758.T", "9984.T", "8035.T", "4063.T"] 

def calculate_rsi(data):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    return 100 - (100 / (1 + (gain / loss)))

def analyze_failures():
    log = []
    n225 = yf.download("^N225", start=START_DATE, interval="1d", progress=False)['Close']
    if isinstance(n225, pd.DataFrame): n225 = n225.iloc[:, 0]
    n225_ma200 = n225.rolling(200).mean()

    for ticker in TICKERS:
        df = yf.download(ticker, start=START_DATE, interval="1d", progress=False)
        if df.empty or len(df) < 50: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df['RSI'] = calculate_rsi(df['Close'])
        df['MA25'] = df['Close'].rolling(25).mean()
        df['Slope'] = df['MA25'].diff(5)
        
        pos = None
        for i in range(25, len(df)):
            date = df.index[i]
            curr = df['Close'].iloc[i]
            rsi = df['RSI'].iloc[i]
            is_bull = n225.loc[:date].iloc[-1] > n225_ma200.loc[:date].iloc[-1]
            regime = "BULL (RSI<35)" if is_bull else "BEAR (RSI<25)"
            threshold = 35 if is_bull else 25
            
            if pos is None:
                if rsi < threshold and df['Slope'].iloc[i] > -curr * 0.005:
                    pos = {"entry": curr, "date": date, "regime": regime, "rsi_at_entry": rsi}
            else:
                p_diff = (curr / pos['entry'] - 1)
                days = (date - pos['date']).days
                if p_diff >= 0.05 or p_diff <= -0.03 or days > 15:
                    log.append({
                        "Ticker": ticker,
                        "Entry_Date": pos['date'].strftime('%Y-%m-%d'),
                        "Regime": pos['regime'],
                        "RSI_Entry": round(pos['rsi_at_entry'], 1),
                        "Result%": round(p_diff * 100, 2),
                        "Days": days
                    })
                    pos = None
    return pd.DataFrame(log)

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("CASE STUDY: Detailed Trade Log of Adaptive Model\n")
    df = analyze_failures()
    print(df.to_string(index=False))
    
    # 失敗の分析
    losses = df[df['Result%'] < 0]
    print("\n" + "="*70)
    print("ANALYSIS OF THE 'BULL REGIME' TRAP")
    print("="*70)
    print(f"Total Losses: {len(losses)}")
    bull_losses = len(losses[losses['Regime'].str.contains("BULL")])
    print(f"Losses in 'BULL' Mode (RSI<35): {bull_losses}")
    print("-" * 70)
    print("INSIGHT: 地合いが良い（BULL）時に RSI < 35 まで条件を緩めたせいで、")
    print("本来「まだ高い」場所でエントリーしてしまい、その後の調整に捕まっているパターンが多いなのだ！🥇")

if __name__ == "__main__":
    main()
