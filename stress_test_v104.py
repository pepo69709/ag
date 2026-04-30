import numpy as np
import pandas as pd
import yfinance as yf

# ===========================================================================
# Sniper AI V104: Stress Test (Reality Check Edition)
# 役割: 手数料とスリッページを厳密に適用し、銘柄ごとの「期待値の安定性」を検証する。
# ===========================================================================

TICKERS = ["6857.T", "6146.T", "8035.T", "8766.T", "4063.T"]
INTERVAL = "60m"
PERIOD = "2y"
FEE = 0.001       # 手数料 0.1%
SLIPPAGE = 0.001  # スリッページ 0.1%

def load(ticker):
    df = yf.download(ticker, period=PERIOD, interval=INTERVAL, progress=False)
    if df.empty: return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def backtest(df):
    df = df.copy()
    df["sma20"] = df["Close"].rolling(20).mean()
    df["sma50"] = df["Close"].rolling(50).mean()
    
    in_pos = False
    entry = 0
    trades = []
    
    for i in range(50, len(df) - 1):
        try:
            # 最新の確定足で判定
            trend = df["sma20"].iloc[i] > df["sma50"].iloc[i]
            # 3時間安値更新なし
            exhaustion = df["Low"].iloc[i-2:i+1].min() >= df["Low"].iloc[i-3]
            
            if not in_pos and trend and exhaustion:
                entry = df["Open"].iloc[i+1] # 翌始値エントリー
                in_pos = True
            elif in_pos:
                exit_price = df["Close"].iloc[i]
                pnl = (exit_price / entry) - 1
                
                # エグジット条件 (3%利確 / 2%損切相当)
                if pnl >= 0.03 or exit_price < (df["sma20"].iloc[i] * 0.98):
                    # コスト（往復手数料+スリッページ）を差し引く
                    real_pnl = pnl - (FEE + SLIPPAGE)
                    trades.append(real_pnl)
                    in_pos = False
        except:
            continue
    return np.array(trades)

def metrics(trades):
    if len(trades) == 0: return None
    wins = trades[trades > 0]
    losses = trades[trades <= 0]
    
    pf = wins.sum() / abs(losses.sum() + 1e-9)
    winrate = len(wins) / len(trades)
    
    return {
        "PF": pf,
        "Trades": len(trades),
        "WinRate": winrate,
        "Mean": trades.mean() * 100,
        "Worst": trades.min() * 100
    }

def run():
    results = []
    print(f"[*] Running Reality Check Audit (Total Cost: {(FEE+SLIPPAGE)*100:.2f}%)...")
    for t in TICKERS:
        df = load(t)
        if df is None or len(df) < 200: continue
        trades = backtest(df)
        m = metrics(trades)
        if m:
            m["Ticker"] = t
            results.append(m)
            print(f"   {t:8} | PF: {m['PF']:.4f} | Trades: {m['Trades']}")

    if not results: return
    res = pd.DataFrame(results)
    
    print("\n" + "="*70)
    print("REALITY CHECK AUDIT: FINAL RESULT")
    print("="*70)
    print(res.sort_values("PF", ascending=False).to_string(index=False))
    print("-" * 70)
    print("SYSTEM STABILITY ANALYSIS")
    print("-" * 70)
    print(f"Average PF     : {res['PF'].mean():.4f}")
    print(f"Worst PF       : {res['PF'].min():.4f}")
    print(f"PF Std Dev     : {res['PF'].std():.4f} (Low is better)")
    print(f"Avg Return (%) : {res['Mean'].mean():+.4f}%")
    print("="*70)

if __name__ == "__main__":
    run()
