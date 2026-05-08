import pandas as pd
import numpy as np
import yfinance as yf
import pickle
import os
import requests
from datetime import datetime
from indicators import Indicators
from strategy_core import get_signal

TICKERS = [
    '8035.T', '6920.T', '6146.T', '6857.T', '4063.T', '6501.T',
    '6702.T', '6723.T', '6752.T', '6758.T', '6981.T', '6902.T',
    '6954.T', '7733.T', '7741.T', '6971.T', '7203.T', '7267.T',
    '7269.T', '7201.T', '7261.T', '7270.T', '7272.T', '7011.T',
    '7012.T', '8306.T', '8316.T', '8411.T', '8766.T', '8725.T',
    '8604.T', '8750.T', '7182.T', '8001.T', '8002.T', '8031.T',
    '8053.T', '8058.T', '5020.T', '5019.T', '9984.T', '9432.T',
    '9433.T', '9434.T', '4689.T', '3659.T', '4755.T', '9983.T',
    '8267.T', '7974.T', '2413.T', '3382.T', '4502.T', '4503.T',
    '4519.T', '4568.T', '4507.T', '6367.T', '6301.T', '6326.T',
    '7832.T', '6113.T', '4183.T', '4188.T', '4204.T', '3407.T',
    '5401.T', '5406.T', '8802.T', '8801.T', '8830.T', '1928.T',
    '1925.T', '2802.T', '2503.T', '2587.T', '2269.T', '6098.T',
    '4661.T', '9602.T', '9201.T', '1458.T', '1459.T', '1357.T'
]

def run_cloud_scan():
    print('[CLOUD] V9.9 Cloud Scan Started...')
    gas_url = os.environ.get('GAS_WEBAPP_URL')
    with open('models/model_lgbm.pkl', 'rb') as f: lgbm = pickle.load(f)
    with open('models/model_clf.pkl',  'rb') as f: clf  = pickle.load(f)
    with open('models/feature_cols.pkl', 'rb') as f: f_cols = pickle.load(f)

    n = yf.download('^N225', period='1mo', progress=False)
    j = yf.download('JPY=X', period='1mo', progress=False)
    if isinstance(n.columns, pd.MultiIndex): n.columns = n.columns.get_level_values(0)
    if isinstance(j.columns, pd.MultiIndex): j.columns = j.columns.get_level_values(0)
    mt = (n['Close'].iloc[-1]/n['Close'].rolling(20).mean().iloc[-1]-1)*100
    fr = j['Close'].pct_change(5).iloc[-1]*100
    mv = (Indicators.atr(n).iloc[-1]/n['Close'].iloc[-1])*100

    strong_results = []
    for t in TICKERS:
        d = yf.download(t, period='2y', progress=False)
        if d.empty or len(d)<250: continue
        if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
        c = d['Close']
        p = float(c.iloc[-1])
        rsi = Indicators.rsi(d).iloc[-1]
        ml, ms = Indicators.macd(d)
        bu, bm, bl = Indicators.bbands(d)
        atr, adx = Indicators.atr(d).iloc[-1], Indicators.adx(d).iloc[-1]
        s20, s50, s200 = c.rolling(20).mean().iloc[-1], c.rolling(50).mean().iloc[-1], c.rolling(200).mean().iloc[-1]
        v20 = d['Volume'].rolling(20).mean().iloc[-1]
        h250 = d['High'].rolling(250).max().iloc[-1]
        f_dict = {
            'RSI': rsi, 'MACD': ml.iloc[-1], 'MACD_Signal': ms.iloc[-1],
            'BB_Upper': bu.iloc[-1], 'BB_Mid': bm.iloc[-1], 'BB_Lower': bl.iloc[-1],
            'ATR': atr, 'ADX': adx, 'SMA_20': s20, 'SMA_50': s50, 'SMA_200': s200,
            'kairi_20': (p/s20-1)*100, 'kairi_200': (p/s200-1)*100, 'vol_ratio': float(d['Volume'].iloc[-1])/(v20+1e-9),
            'return_lag_1': c.pct_change(1).iloc[-1]*100, 'rsi_lag_1': Indicators.rsi(d).iloc[-2],
            'return_lag_2': c.pct_change(1).iloc[-2]*100, 'rsi_lag_2': Indicators.rsi(d).iloc[-3],
            'return_lag_3': c.pct_change(1).iloc[-2]*100, 'rsi_lag_3': Indicators.rsi(d).iloc[-4],
            'high_52w_ratio': p/(h250+1e-9), 'roc_20': c.pct_change(20).iloc[-1]*100,
            'bb_position': (p-bl.iloc[-1])/(bu.iloc[-1]-bl.iloc[-1]+1e-9),
            'atr_compression': Indicators.atr(d,7).iloc[-1]/Indicators.atr(d,30).iloc[-1],
            'vol_trend': d['Volume'].rolling(5).mean().iloc[-1]/(v20+1e-9),
            'mkt_trend': mt, 'fx_roc': fr, 'mkt_vol': mv
        }
        X = pd.DataFrame([f_dict])[f_cols]
        ev = float(lgbm.predict(X)[0])
        pb = float(clf.predict_proba(X)[0][1])
        v = Indicators.get_pattern_score(d)
        threshold = 0.60 if mv > 2.0 else 0.55
        is_s = (get_signal(d) and pb >= threshold and p <= 15000 and v >= 65)
        if is_s:
            strong_results.append({
                'ticker': t, 'price': round(p, 1), 'prob': round(pb*100, 1),
                'ev': round(ev*100, 2), 'vcp': v, 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'features': f_dict # 全特徴量を記録
            })


    # --- GAS & Discord 送信データ準備 ---
    discord_url = os.environ.get("DISCORD_WEBHOOK")
    market_state = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'mkt_vol': round(mv, 2),
        'mkt_trend': round(mt, 2),
        'fx_roc': round(fr, 2),
        'count': len(strong_results)
    }

    # --- GAS送信 (市場環境データも含めて全パトロールを記録) ---
    if gas_url:
        payload = {
            'market': market_state,
            'signals': strong_results
        }
        try: requests.post(gas_url, json=payload, timeout=30)
        except: pass

    if strong_results:
        # --- Discord送信 ---
        if discord_url:
            content = f"🎯 **SNIPER STRONG SIGNAL DETECTED!** (Vol:{market_state['mkt_vol']})\n"
            for s in strong_results:
                content += f"\n> **{s['ticker']}** ({s['price']}円)\n> 勝率: {s['prob']}% / 期待値: {s['ev']}%\n"
            try: requests.post(discord_url, json={'content': content}, timeout=30)
            except: pass

        # --- 蓄積型CSV保存 (将来の学習用) ---
        history_file = "sniper_audit_history.csv"
        new_df = pd.DataFrame(strong_results)
        
        # 特徴量を文字列化
        if 'features' in new_df.columns:
            new_df['features'] = new_df['features'].apply(lambda x: str(x))
            
        if os.path.exists(history_file):
            try:
                old_df = pd.read_csv(history_file)
                final_df = pd.concat([old_df, new_df], ignore_index=True)
            except: final_df = new_df
        else:
            final_df = new_df
            
        final_df.to_csv(history_file, index=False)
        print(f"[CLOUD] Detection success! {len(strong_results)} signals appended to {history_file}")


    else:
        print("[CLOUD] No STRONG signals detected.")
        if discord_url:
            # 6時間に1回くらいは生存報告を送る（あるいは送らない設定も可）
            pass



if __name__ == '__main__':
    run_cloud_scan()