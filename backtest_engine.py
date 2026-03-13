import pandas as pd
import yfinance as yf
import numpy as np
import joblib
import os
from datetime import datetime, timedelta
import config

# ==========================================
# 📊 AI BACKTEST ENGINE: THE TRUTH REVEALER
# ==========================================

print("🚀 バックテスト・エンジン起動。過去のデータで AI の『本気』を検証します...")

def calculate_historical_features(df):
    """
    全期間のテクニカル指標を一括計算（ベクトル処理）
    """
    close = df['Close']
    volume = df['Volume']
    
    # 指標計算
    sma25 = close.rolling(window=25).mean()
    sma50 = close.rolling(window=50).mean()
    dev = (close / sma25 - 1) * 100
    
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi = 100 - (100 / (1 + (gain / loss.replace(0, 1e-6)).fillna(0)))
    
    vol_ratio = volume / volume.rolling(window=20).mean()
    daily_return = close.pct_change()
    volatility = daily_return.rolling(window=10).std() * np.sqrt(252) * 100
    
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    macd_hist = macd - macd_signal
    
    std25 = close.rolling(window=25).std()
    bb_pos = (close - sma25) / (std25 * 2) * 100
    
    gap = (df['Open'] / close.shift(1) - 1) * 100
    
    features = pd.DataFrame({
        'feat_price': close,
        'feat_dev': dev,
        'feat_rsi': rsi,
        'feat_vol': vol_ratio,
        'feat_volatility': volatility,
        'feat_trend': sma25 / sma50,
        'feat_macd': macd_hist,
        'feat_bb_pos': bb_pos,
        'feat_gap': gap
    })
    
    # 曜日データ (0=Mon, 6=Sun)
    features['feat_dayofweek'] = df.index.dayofweek
    
    return features.dropna()

def run_backtest():
    # モデルロード
    try:
        xgb_model = joblib.load("xgb_model.pkl")
        lgbm_model = joblib.load("lgbm_model.pkl")
    except:
        print("❌ モデルが見つかりません。")
        return

    # テスト対象（時間短縮のため主要な50銘柄をサンプリング）
    tickers = config.WATCH_LIST[:50] 
    
    total_signals = 0
    wins = 0
    losses = 0
    
    # マクロ指標（簡略化：今回は個別株のテクニカルのみで検証）
    # 本来は日経平均も必要だが、まずは個別株の感度を見る
    n_trend, n_vol, n_phase = 0.0, 20.0, 1.0 

    print(f"🔍 {len(tickers)} 銘柄で過去3ヶ月の抜き打ちテストを開始...")

    for ticker in tickers:
        try:
            data = yf.download(ticker, period="4mo", progress=False, auto_adjust=True)
            if data.empty: continue
            
            features = calculate_historical_features(data)
            
            # 過去の各日を「最新」と見立てて予測
            # 未来が見えないように、i日目のデータで判定し、i+1〜i+5日で結末を見る
            for i in range(len(features) - 6):
                # i日目の特徴量
                row = features.iloc[i]
                
                # スパルタ・フィルター条件のチェック (乖離率/RSI)
                if not (config.ENTRY_DEV_MIN <= row['feat_dev'] <= config.ENTRY_DEV_MAX): continue
                if not (config.ENTRY_RSI_MIN <= row['feat_rsi'] <= config.ENTRY_RSI_MAX): continue
                
                f_input = pd.DataFrame([{
                    'feat_price': row['feat_price'], 'feat_dev': row['feat_dev'], 'feat_rsi': row['feat_rsi'],
                    'feat_vol': row['feat_vol'], 'feat_volatility': row['feat_volatility'], 
                    'feat_trend': row['feat_trend'], 'feat_dayofweek': row['feat_dayofweek'],
                    'feat_macd': row['feat_macd'], 'feat_bb_pos': row['feat_bb_pos'], 'feat_gap': row['feat_gap'],
                    'feat_nikkei_trend': n_trend, 'feat_fear_index': n_vol, 'feat_market_phase': n_phase
                }])
                
                prob_xgb = xgb_model.predict_proba(f_input)[0][1]
                prob_lgbm = lgbm_model.predict_proba(f_input)[0][1]
                avg_prob = (prob_xgb + prob_lgbm) / 2
                
                # 地獄のスパルタ基準 (85%以上 & 両者合意)
                if avg_prob >= 0.85 and prob_xgb >= 0.80 and prob_lgbm >= 0.80:
                    total_signals += 1
                    
                    # 結末を確認 (i+1日から最大5日間)
                    entry_price = data['Close'].iloc[i]
                    success = False
                    stop_out = False
                    
                    for day in range(1, 6):
                        future_high = data['High'].iloc[i+day]
                        future_low = data['Low'].iloc[i+day]
                        
                        # 先に利確(+1.0%)に届いたか？
                        if ((future_high / entry_price) - 1) * 100 >= 1.0:
                            success = True
                            break
                        # 先に損切(-2.0%)に届いたか？
                        if ((future_low / entry_price) - 1) * 100 <= -2.0:
                            stop_out = True
                            break
                    
                    if success:
                        wins += 1
                    elif stop_out:
                        losses += 1
                        
        except Exception as e:
            continue

    print("\n" + "="*50)
    print("🏆 【検証結果：AI 抜き打ちテスト】")
    print("="*50)
    print(f"📅 検証期間: 過去3ヶ月")
    print(f"🎯 目標利益: +1.0% / 損切り: -2.0%")
    print(f"📊 検知された『黄金シグナル』回数: {total_signals}回")
    
    if total_signals > 0:
        win_rate = (wins / total_signals) * 100
        print(f"✅ 平均勝率 (的中率): {win_rate:.1f}%")
        print(f"👍 成功回数: {wins}回")
        print(f"👎 失敗回数: {losses}回")
        print(f"⏳ 判定継続中（5日以内決着つかず）: {total_signals - wins - losses}回")
        
        if win_rate >= 80:
            print("\n👑 評価: 【極めて優秀】 住友電工の奇跡は、偶然ではありませんでした。")
        elif win_rate >= 60:
            print("\n👌 評価: 【良好】 堅実な資産形成が期待できるレベルです。")
        else:
            print("\n⚠️ 評価: 【改善の余地あり】 基準をさらに厳しくする必要があります。")
    else:
        print("\n😱 評価: シグナルが一度も出ませんでした。基準が厳しすぎるか、今の相場に合っていません。")

if __name__ == "__main__":
    run_backtest()
