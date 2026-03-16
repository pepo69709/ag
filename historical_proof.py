import pandas as pd
import yfinance as yf
import numpy as np
import joblib
from datetime import datetime, timedelta
import config

print("🛡️ 【究極の証明：AI 過去の目利きテスト（1.0%ターゲット）】")
print("2週間前の相場において、AIが『買い』と判断した銘柄がその後どうなったか、改竄なしで検証します。")

def calculate_metrics_raw(df, i):
    if i < 70: return None
    try:
        d = df.iloc[i-70 : i+1]
        close = d['Close'].iloc[:, 0] if isinstance(d['Close'], pd.DataFrame) else d['Close']
        open_p = d['Open'].iloc[:, 0] if isinstance(d['Open'], pd.DataFrame) else d['Open']
        close = pd.to_numeric(close).dropna()
        sma25 = close.rolling(window=25).mean()
        sma50 = close.rolling(window=50).mean()
        dev = (close / sma25 - 1) * 100
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss.replace(0, 1e-6)).fillna(0)))
        volat = close.pct_change().rolling(window=10).std() * np.sqrt(252) * 100
        macd = (close.ewm(span=12).mean() - close.ewm(span=26).mean())
        macd_hist = macd - macd.ewm(span=9).mean()
        return {
            "price": float(close.iloc[-1]), "dev": float(dev.iloc[-1]), "rsi": float(rsi.iloc[-1]),
            "trend": float((sma25/sma50).iloc[-1]), "macd": float(macd_hist.iloc[-1]),
            "volat": float(volat.iloc[-1]), "weekday": d.index[-1].weekday()
        }
    except: return None

model_xgb = joblib.load("xgb_model.pkl")
model_lgbm = joblib.load("lgbm_model.pkl")

# さらに翌日の木曜日（2/26）をテスト台にする
test_date = "2026-02-26"
print(f"📅 検証基準日: {test_date}")

tickers = config.WATCH_LIST[:50]
past_candidates = []

for ticker in tickers:
    try:
        # 基準日前後のデータを取得
        data = yf.download(ticker, start="2025-10-01", end="2026-03-10", progress=False, auto_adjust=True)
        if data.empty: continue
        
        # 基準日のインデックスを探す
        idx_list = data.index.strftime('%Y-%m-%d').tolist()
        if test_date not in idx_list:
            # 近い日を探す
            available = [d for d in idx_list if d <= test_date]
            if not available: continue
            current_date_str = available[-1]
        else:
            current_date_str = test_date
            
        current_idx = idx_list.index(current_date_str)
        m = calculate_metrics_raw(data, current_idx)
        if not m: continue
        
        f_input = pd.DataFrame([{
            'feat_price': m['price'], 'feat_dev': m['dev'], 'feat_rsi': m['rsi'],
            'feat_vol': 1.0, 'feat_volatility': m['volat'], 
            'feat_trend': m['trend'], 'feat_dayofweek': m['weekday'],
            'feat_macd': m['macd'], 'feat_bb_pos': 0.0, 'feat_gap': 0.0,
            'feat_nikkei_trend': 2.0, 'feat_fear_index': 20.0, 'feat_market_phase': 1
        }])
        
        prob = (model_xgb.predict_proba(f_input)[0][1] + model_lgbm.predict_proba(f_input)[0][1]) / 2
        
        # 結果の確認 (5日間)
        e_p = float(data['Close'].iloc[current_idx].item()) if hasattr(data['Close'].iloc[current_idx], 'item') else float(data['Close'].iloc[current_idx])
        outcome = 0
        for d in range(1, 6):
            if current_idx + d >= len(data): break
            hi = data['High'].iloc[current_idx+d]
            lo = data['Low'].iloc[current_idx+d]
            hi_val = float(hi.item()) if hasattr(hi, 'item') else float(hi)
            lo_val = float(lo.item()) if hasattr(lo, 'item') else float(lo)
            
            if ((hi_val / e_p) - 1) * 100 >= 1.0: outcome = 1; break
            if ((lo_val / e_p) - 1) * 100 <= -2.0: break
            
        print(f"Checked {ticker}: Date={current_date_str}, Prob={prob:.4f}, Win={outcome}")
        past_candidates.append({"ticker": ticker, "prob": prob, "win": outcome})
    except Exception as e:
        print(f"Error on {ticker}: {e}")
        continue
if not past_candidates:
    print("❌ 有効な判定がありませんでした。")
else:
    df = pd.DataFrame(past_candidates).sort_values(by="prob", ascending=False)
    top_10 = df.head(10)

    print("\n📊 【2/25時点のAI予測 TOP 10 とその後の結果】")
    print(top_10.to_string(index=False))

    total_win = top_10['win'].sum()
    print(f"\n📈 TOP 10 の的中率: {total_win * 10}%")
    print(f"💡 AIが『良い』と判断した10銘柄のうち、{total_win}銘柄が実際に5日以内に+1.0%を達成しました。")
