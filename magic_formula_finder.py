import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
import japanize_matplotlib
import config

def hunt_magic_combination():
    # 主要30銘柄で過去10年分の「全データ」を収集
    tickers = config.WATCH_LIST[:30]
    master_records = []

    print("\n" + "="*80)
    print("      【多変量・相関ハンティング】最強の組み合わせを探索中...")
    print("="*80)

    for ticker in tickers:
        print(f">> 調査中: {ticker}...", end="\r")
        df = yf.download(ticker, period="10y", interval="1d", progress=False)
        if df.empty: continue
        
        # yfinanceの戻り値がMultiIndexになる場合があるため、明示的に列を選択してSeries化
        if isinstance(df.columns, pd.MultiIndex):
            close = df['Close'].iloc[:, 0]
            volume = df['Volume'].iloc[:, 0]
            open_p = df['Open'].iloc[:, 0]
        else:
            close = df['Close']
            volume = df['Volume']
            open_p = df['Open']

        # --- Indicator 1: 25日線乖離率 (トレンドの歪み) ---
        sma25 = close.rolling(window=25).mean()
        dev = (close / sma25 - 1) * 100
        
        # --- Indicator 2: RSI ---
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss.replace(0, np.nan)).fillna(0)))
        
        # --- Indicator 3: 出来高レシオ ---
        vol_ratio = volume / volume.rolling(window=20).mean()
        
        # --- Indicator 4: ボリンジャーバンド位置 ---
        std = close.rolling(window=25).std()
        bb_upper = sma25 + (std * 2)
        bb_lower = sma25 - (std * 2)
        bb_pos = (close - bb_lower) / (bb_upper - bb_lower)

        # 全てをまとめる
        new_df = pd.DataFrame({
            'Close': close,
            'Dev': dev,
            'RSI': rsi,
            'Vol_Ratio': vol_ratio,
            'BB_Pos': bb_pos,
            'Future_Return': (close.shift(-3) / close - 1) * 100
        }).dropna()
        
        master_records.append(new_df)

    full_df = pd.concat(master_records)

    # --- 分析：2変数の組み合わせ効果 ---
    # 例：RSI(横軸) × 乖離率(縦軸) で、将来のリターンがどう変わるか？
    full_df['RSI_Bin'] = pd.cut(full_df['RSI'], bins=range(0, 101, 10))
    full_df['Dev_Bin'] = pd.cut(full_df['Dev'], bins=range(-15, 16, 3))
    
    # 平均リターンのヒートマップ
    heatmap_data = full_df.pivot_table(values='Future_Return', index='Dev_Bin', columns='RSI_Bin', aggfunc='mean')

    plt.figure(figsize=(14, 8))
    sns.heatmap(heatmap_data, annot=True, fmt=".2f", cmap='RdYlGn', center=0)
    plt.title("【魔法の式 探索図】乖離率 × RSI の組み合わせと将来リターン")
    plt.xlabel("RSI (値が小さいほど売られすぎ)")
    plt.ylabel("25日線乖離率 (マイナスほど売られすぎ)")
    
    # 結論の導き出し
    best_cell = heatmap_data.stack().idxmax()
    print("\n\n" + "*"*80)
    print("      【探索結果：最強の勝機】")
    print("*"*80)
    print(f"もっともリターンが高かったゾーン:")
    print(f" -> 乖離率: {best_cell[0]}")
    print(f" -> RSI   : {best_cell[1]}")
    print(f" -> 平均期待リターン: {heatmap_data.loc[best_cell]:.2f}%")
    print("*"*80)
    
    plt.show()

if __name__ == "__main__":
    hunt_magic_combination()
