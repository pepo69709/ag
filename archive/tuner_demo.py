import yfinance as yf
import pandas as pd
import numpy as np
import sys
import io

# --- 🧠 Sniper AI: 重み付け最適化のデモ (Weight Tuner) ---
# 司令官の疑問：「重みをどう変えると、結果がどう変わるのか？」に答えます。

def simulate_with_weights(df, rsi_weight, vol_weight):
    # スコア計算: (30-RSI) * rsi_weight + (出来高変化) * vol_weight
    df['score'] = (30 - df['rsi']) * rsi_weight + (df['vol_ratio'] - 1) * 100 * vol_weight
    
    trades = []
    for i in range(1, len(df)):
        if df['score'].iloc[i] > 50: # スコア50以上でエントリー
            entry_p = df['Close'].iloc[i]
            # 翌日のリターンをチェック
            if i + 1 < len(df):
                exit_p = df['Close'].iloc[i+1]
                trades.append((exit_p / entry_p - 1) * 100)
    
    return np.mean(trades) if trades else 0

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    ticker = "7203.T" # トヨタで実験
    df = yf.download(ticker, period="2y", progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # 指標作成
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
    df['vol_ratio'] = df['Volume'] / df['Volume'].rolling(5).mean().shift(1)

    print(f"--- 🎯 Weight Optimization Demo: {ticker} ---")
    
    # パターン1: RSI重視（逆張りスタイル）
    p1_profit = simulate_with_weights(df, rsi_weight=2.0, vol_weight=0.1)
    # パターン2: 出来高重視（モメンタムスタイル）
    p2_profit = simulate_with_weights(df, rsi_weight=0.1, vol_weight=2.0)
    
    print(f"Pattern A (RSI Heavy) Avg Profit: {p1_profit:.2f}%")
    print(f"Pattern B (Vol Heavy) Avg Profit: {p2_profit:.2f}%")
    
    print("\n💡 解説:")
    print("AIはこの『平均利益』が最大になるような「重み（Weight）」の組み合わせを、")
    print("過去10年〜20年の膨大なデータから探し出します。")
    print("現在は私がバックテストで見つけた『黄金比』を固定で使っていますが、")
    print("V2ではこの計算を毎日自動で行い、重みを更新し続けるのが『学習』の正体なのだ！🥇🦾✨")

if __name__ == "__main__":
    main()
