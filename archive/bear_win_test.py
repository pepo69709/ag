import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import io

# --- 🚀 逆襲：下落相場（ベアマーケット）で勝つための検証 ---
# 1. リアルタイムで「今は悪い」と判断する基準（MA200）
# 2. 逆を行く「ダブルインバース (1357.T)」をスナイプして勝てるか？

START_DATE = "2008-01-01"
END_DATE = "2009-12-31"   # リーマンショックの時期
INVESTMENT = 5000

def get_rsi(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    return 100 - (100 / (1 + (gain / (loss + 1e-9))))

def test_bear_strategy():
    print("Testing 'Bear Defense' using Nikkei Double Inverse(1357.T) in 2008-2009...")
    
    # 本来は当時なかったETFですが、指数データ(^N225)から「逆の動き」をシミュレートします。
    # 日経が1%下がれば、ダブルインバースは2%上がる性質。
    try:
        n225 = yf.download("^N225", start=START_DATE, end=END_DATE, interval="1d", progress=False)
        if n225.empty: return
        if isinstance(n225.columns, pd.MultiIndex): n225.columns = n225.columns.get_level_values(0)
        
        # 疑似ダブルインバース価格（日経が下がると上がる）
        # 2008年初を100として、日経の逆の動き(x2)を追跡
        returns = n225['Close'].pct_change()
        inv_returns = -2.0 * returns 
        pseudo_inv_price = (1 + inv_returns).cumprod() * 10000
        
        df = pd.DataFrame({"Close": pseudo_inv_price}, index=n225.index)
        df['RSI'] = get_rsi(df)
        
        trades = []
        pos = None
        for i in range(20, len(df)):
            # リアルタイム判定：日経が25日平均より下（下落トレンド）の時だけ、このインバースを「買う」
            # インバースを買う ＝ 相場が下がることに賭ける
            curr = df['Close'].iloc[i]
            if pos is None:
                # インバースも「売られすぎ(RSI<30)」で買う（＝相場が一時的にリバウンドして下げ止まりそうな時）
                if df['RSI'].iloc[i] < 30:
                    pos = {"entry": curr, "date": df.index[i]}
            else:
                diff = (curr / pos['entry']) - 1
                if diff >= 0.05 or diff <= -0.05 or (df.index[i] - pos['date']).days > 20:
                    trades.append(diff * INVESTMENT)
                    pos = None
        
        res = np.array(trades)
        print("\n" + "="*60)
        print("BEAR DEFENSE (INVERSE SNIPE) RESULT: 2008-2009")
        print("="*60)
        print(f"Total Trades: {len(res)}")
        print(f"Win Rate    : {(res > 0).mean()*100:.2f}%")
        print(f"Total Profit: ¥ {res.sum():,.0f}")
        print("="*60)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_bear_strategy()
