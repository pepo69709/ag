import yfinance as yf
import pandas as pd
import numpy as np
import config
from datetime import datetime, timedelta
import os

# ==========================================
# 📊 DATA-GENERATOR: AI学習用データ生成スクリプト (バグ完全修正版)
# ==========================================

YEARS_TO_FETCH = 3
SAMPLE_INTERVAL = 10 

def generate_training_data():
    print(f"🚀 AI特訓用データの生成を開始します... (対象期間: 過去{YEARS_TO_FETCH}年)")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * YEARS_TO_FETCH)
    
    training_data = []
    total_tickers = len(config.WATCH_LIST)

    print("🌍 日経平均のマクロデータを取得中...")
    try:
        nikkei = yf.download("^N225", start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False, auto_adjust=True)
        if isinstance(nikkei.columns, pd.MultiIndex):
            nikkei_close = nikkei['Close'].iloc[:, 0]
        else:
            nikkei_close = nikkei['Close']
        nikkei_close = pd.to_numeric(nikkei_close, errors='coerce').dropna()
        nikkei_trend_20d = nikkei_close.pct_change(periods=20) * 100
        nikkei_returns = nikkei_close.pct_change()
        nikkei_vol = nikkei_returns.rolling(window=20).std() * np.sqrt(252) * 100
        def classify_regime(x):
            if pd.isna(x): return 1
            if x > 3.0: return 2
            elif x < -3.0: return 0
            else: return 1
        nikkei_phase = nikkei_trend_20d.apply(classify_regime)
    except Exception as e:
        print(f"日経データの取得に失敗しました: {e}")
        nikkei_trend_20d = pd.Series(dtype=float)
        nikkei_vol = pd.Series(dtype=float)
        nikkei_phase = pd.Series(dtype=float)

    for i, ticker in enumerate(config.WATCH_LIST):
        print(f"[{i+1}/{total_tickers}] 解析中: {ticker}...")
        try:
            hist = yf.download(ticker, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False, auto_adjust=True)
            if hist.empty or len(hist) < 50: continue

            if isinstance(hist.columns, pd.MultiIndex):
                close = hist['Close'].iloc[:, 0]
                high = hist['High'].iloc[:, 0]
                low = hist['Low'].iloc[:, 0]
                open_p = hist['Open'].iloc[:, 0]
                volume = hist['Volume'].iloc[:, 0]
            else:
                close = hist['Close']
                high = hist['High']
                low = hist['Low']
                open_p = hist['Open']
                volume = hist['Volume']

            close = pd.to_numeric(close, errors='coerce')
            high = pd.to_numeric(high, errors='coerce')
            low = pd.to_numeric(low, errors='coerce')
            open_p = pd.to_numeric(open_p, errors='coerce')
            volume = pd.to_numeric(volume, errors='coerce')

            # テクニカル指標計算 (Series の段階で replace を行う)
            sma25 = close.rolling(window=25).mean()
            sma50 = close.rolling(window=50).mean()
            dev = (close / sma25.replace(0, 1e-6) - 1) * 100
            
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi = 100 - (100 / (1 + (gain / loss.replace(0, 1e-6))))
            
            vol_ratio = volume / volume.rolling(window=20).mean().replace(0, 1e-6)
            volat = close.pct_change().rolling(window=10).std() * np.sqrt(252) * 100

            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd_raw = ema12 - ema26
            macd_hist = macd_raw - macd_raw.ewm(span=9, adjust=False).mean()

            bb_std = close.rolling(window=25).std()
            bb_position = (close - sma25) / (bb_std.replace(0, 1e-6) * 2) * 100
            gap_pct = (open_p / close.shift(1).replace(0, 1e-6) - 1) * 100
            
            # Trend 計算も Series の状態で行う
            trend_ratio = sma25 / sma50.replace(0, 1e-6)

            # サンプリング実行
            for date_idx in range(50, len(close) - 5, SAMPLE_INTERVAL):
                entry_price = float(close.iloc[date_idx])
                entry_date = close.index[date_idx]
                f_high = high.iloc[date_idx+1 : date_idx+61].values
                f_low = low.iloc[date_idx+1 : date_idx+61].values
                target_p = entry_price * (1 + (config.EXIT_PROFIT_TARGET / 100))
                stop_p = entry_price * (1 - (config.EXIT_STOP_LOSS / 100))
                
                label = np.nan
                for day_idx in range(len(f_high)):
                    if f_low[day_idx] <= stop_p:
                        label = 0
                        break
                    elif f_high[day_idx] >= target_p:
                        label = 1
                        break
                
                if not np.isnan(label):
                    def get_val(series, date, default):
                        try:
                            d = pd.to_datetime(date).normalize()
                            if d in series.index: return float(series.loc[d])
                            idx = series.index.get_indexer([d], method='pad')[0]
                            return float(series.iloc[idx]) if idx >= 0 else default
                        except: return default

                    n_trend = get_val(nikkei_trend_20d, entry_date, 0.0)
                    n_vol = get_val(nikkei_vol, entry_date, 20.0)
                    n_phase = get_val(nikkei_phase, entry_date, 1.0)

                    training_data.append({
                        "timestamp": entry_date.strftime('%Y-%m-%d'),
                        "ticker": ticker,
                        "feat_price": round(entry_price, 1),
                        "feat_dev": round(float(dev.iloc[date_idx]), 2),
                        "feat_rsi": round(float(rsi.iloc[date_idx]), 2),
                        "feat_vol": round(float(vol_ratio.iloc[date_idx]), 2),
                        "feat_volatility": round(float(volat.iloc[date_idx]), 2),
                        "feat_trend": round(float(trend_ratio.iloc[date_idx]), 2), # 修正済み
                        "feat_dayofweek": entry_date.weekday(),
                        "feat_macd": round(float(macd_hist.iloc[date_idx]), 2),
                        "feat_bb_pos": round(float(bb_position.iloc[date_idx]), 2),
                        "feat_gap": round(float(gap_pct.iloc[date_idx]), 2),
                        "feat_nikkei_trend": round(n_trend, 2),
                        "feat_fear_index": round(n_vol, 2),
                        "feat_market_phase": int(n_phase),
                        "label": int(label)
                    })
        except Exception as e:
            print(f"Error on {ticker}: {e}")
            continue

    if training_data:
        df_train = pd.DataFrame(training_data)
        df_train.to_csv("ai_training_data.csv", index=False, encoding="utf-8-sig")
        print(f"✅ 生成完了: {len(df_train)} 件")
    else: print("❌ データが生成されませんでした。")

if __name__ == "__main__":
    generate_training_data()
