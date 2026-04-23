import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import io

# --- 🚀 高精度・低リスク検証: RSI + ボリンジャーバンド + MACD (500銘柄) ---

TICKERS_BASE = [
    "1332.T", "1605.T", "1801.T", "1925.T", "2502.T", "2914.T", "3382.T", "3402.T", "4063.T", "4452.T",
    "4502.T", "4503.T", "4519.T", "4568.T", "4901.T", "4911.T", "5019.T", "5108.T", "5401.T", "6301.T",
    "6501.T", "6503.T", "6702.T", "6723.T", "6752.T", "6758.T", "6857.T", "6902.T", "6954.T", "6981.T",
    "7011.T", "7203.T", "7267.T", "7733.T", "7741.T", "7974.T", "8001.T", "8031.T", "8035.T", "8058.T",
    "8306.T", "8316.T", "8411.T", "8766.T", "8801.T", "8802.T", "9020.T", "9101.T", "9432.T", "9983.T", "9984.T"
]

START_DATE = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
END_DATE = datetime.now().strftime('%Y-%m-%d')

def calculate_indicators(df):
    # RSI
    delta = df['Close'].diff()
    df['RSI'] = 100 - (100 / (1 + (delta.where(delta > 0, 0).rolling(14).mean() / (-delta.where(delta < 0, 0).rolling(14).mean()))))
    # Bollinger Bands (20, 2)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD20'] = df['Close'].rolling(window=20).std()
    df['BB_Lower'] = df['MA20'] - (df['STD20'] * 2)
    # MACD
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

def run_backtest(ticker, use_bb=False, use_macd=False, stop_loss_pct=0.03):
    try:
        df = yf.download(ticker, start=START_DATE, interval="1d", progress=False)
        if df.empty or len(df) < 30: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df = calculate_indicators(df)
        trades = []
        position = False
        entry_price = 0
        entry_date = None

        for i in range(25, len(df)):
            curr_price = df['Close'].iloc[i]
            rsi = df['RSI'].iloc[i]
            bb_low = df['BB_Lower'].iloc[i]
            macd = df['MACD'].iloc[i]
            macd_sig = df['MACD_Signal'].iloc[i]
            
            # エントリー条件
            entry_signal = (rsi < 30)
            if use_bb: entry_signal = entry_signal and (curr_price < bb_low)
            if use_macd: entry_signal = entry_signal and (macd > macd_sig)

            if not position and entry_signal:
                position = True
                entry_price = curr_price
                entry_date = df.index[i]
            elif position:
                profit_pct = (curr_price / entry_price) - 1
                hold_days = (df.index[i] - entry_date).days
                
                # エグジット判定 (利確 5%, 損切 X%, またはRSI>60)
                if profit_pct >= 0.05 or profit_pct <= -stop_loss_pct or rsi > 60 or hold_days > 15:
                    trades.append(profit_pct * 100)
                    position = False
        return trades
    except: return None

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    configs = [
        {"name": "Standard (RSI only)", "bb": False, "macd": False, "sl": 0.05},
        {"name": "Safe (RSI + BB)", "bb": True, "macd": False, "sl": 0.03},
        {"name": "Confirm (RSI + MACD)", "bb": False, "macd": True, "sl": 0.03},
        {"name": "Ultimate (All + Stop 2%)", "bb": True, "macd": True, "sl": 0.02}
    ]
    
    print(f"Running Multi-Indicator & Risk Management Test on {len(TICKERS_BASE)} tickers...")
    
    for config in configs:
        all_trades = []
        for t in TICKERS_BASE:
            res = run_backtest(t, config['bb'], config['macd'], config['sl'])
            if res: all_trades.extend(res)
        
        if all_trades:
            trades = np.array(all_trades)
            win_rate = (trades > 0).mean() * 100
            print(f"\n[{config['name']}]")
            print(f"  Trades  : {len(trades)}")
            print(f"  Win Rate: {win_rate:.2f}%")
            print(f"  Avg P/L : {trades.mean():.2f}%")
            print(f"  Sum P/L : {trades.sum():.2f}%")

if __name__ == "__main__":
    main()
