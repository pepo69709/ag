import pandas as pd

def get_signal(df):
    """
    Sniper AI 共通ロジック (V110 Frozen Spec)
    SMA20 > SMA50 且つ 3時間安値枯渇
    """
    try:
        if len(df) < 50:
            return False

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # SMA計算
        sma20 = df['Close'].rolling(20).mean().iloc[-1]
        sma50 = df['Close'].rolling(50).mean().iloc[-1]

        # 3時間枯渇判定 (直近3時間の安値が、その1時間前の安値以上)
        # つまり、売り圧力が止まったことを示す
        exhaustion = df['Low'].iloc[-3:].min() >= df['Low'].iloc[-4]

        return (sma20 > sma50) and exhaustion
    except:
        return False
