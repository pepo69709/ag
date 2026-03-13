import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
import joblib
from datetime import datetime, timezone, timedelta
import config

# ==========================================
# 🧠 AI-SCANNER：合議制 (Ensemble) パトロールシステム
# ==========================================

JST = timezone(timedelta(hours=9))

def calculate_metrics(df):
    if df is None or df.empty or len(df) < 50: return None
    try:
        if isinstance(df.columns, pd.MultiIndex):
            open_p = df['Open'].iloc[:, 0]
            close = df['Close'].iloc[:, 0]
            volume = df['Volume'].iloc[:, 0]
        else:
            open_p = df['Open']
            close = df['Close']
            volume = df['Volume']

        open_p = pd.to_numeric(open_p, errors='coerce')
        close = pd.to_numeric(close, errors='coerce').dropna()
        sma25 = close.rolling(window=25).mean()
        dev = (close / sma25.replace(0, 1e-6) - 1) * 100
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss.replace(0, 1e-6)).fillna(0)))
        vol_ratio = volume / volume.rolling(window=20).mean().replace(0, 1e-6)
        
        daily_return = close.pct_change()
        volatility = daily_return.rolling(window=10).std() * np.sqrt(252) * 100
        sma50 = close.rolling(window=50).mean()
        trend_sma = (sma25 / sma50.replace(0, 1e-6))
        
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        macd_hist = macd - macd_signal
        
        std25 = close.rolling(window=25).std()
        bb_position = (close - sma25) / (std25.replace(0, 1e-6) * 2) * 100
        
        prev_close = close.shift(1)
        gap_pct = (open_p / prev_close.replace(0, 1e-6) - 1) * 100

        # 一目均衡表（簡略版）
        tenkan = (close.rolling(window=9).max() + close.rolling(window=9).min()) / 2
        kijun = (close.rolling(window=26).max() + close.rolling(window=26).min()) / 2
        feat_ichimoku = (close / kijun.replace(0, 1e-6) - 1) * 100
        
        # 出来高の勢い (Volume Trend)
        vol_ema5 = volume.ewm(span=5).mean()
        vol_ema20 = volume.ewm(span=20).mean()
        feat_vol_trend = (vol_ema5 / vol_ema20.replace(0, 1e-6) - 1) * 100
        
        return {
            "price": float(close.iloc[-1]),
            "dev": float(dev.iloc[-1]),
            "rsi": float(rsi.iloc[-1]),
            "vol_ratio": float(vol_ratio.iloc[-1]),
            "volatility": float(volatility.iloc[-1]),
            "trend": float(trend_sma.iloc[-1]),
            "macd": float(macd_hist.iloc[-1]),
            "bb_pos": float(bb_position.iloc[-1]),
            "gap": float(gap_pct.iloc[-1])
        }
    except Exception as e:
        print(f"Metrics Error: {e}")
        return None

def run_trainer_scan():
    now_jst = datetime.now(JST)
    unique_tickers = list(dict.fromkeys(config.WATCH_LIST))
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL") or config.DISCORD_WEBHOOK_URL
    
    print(f"🚀 【1.0% エリート・スキャナー】起動: {now_jst}")
    
    try:
        # --- 🤖 AI用マクロ指標の取得 (日経平均) ---
        print("🌍 市場マクロ（日経平均）の状態を分析中...")
        n_trend, n_vol, n_phase = 0.0, 20.0, 1.0
        try:
            nikkei = yf.download("^N225", period="3mo", progress=False, auto_adjust=True)
            if isinstance(nikkei.columns, pd.MultiIndex):
                n_close = nikkei['Close'].iloc[:, 0]
            else:
                n_close = nikkei['Close']
            
            n_close = pd.to_numeric(n_close, errors='coerce').dropna()
            if len(n_close) >= 20:
                n_trend = float((n_close.iloc[-1] / n_close.iloc[-20] - 1) * 100)
                n_returns = n_close.pct_change()
                n_vol = float(n_returns.rolling(window=20).std().iloc[-1] * np.sqrt(252) * 100)
                if n_trend > 3.0: n_phase = 2
                elif n_trend < -3.0: n_phase = 0
                else: n_phase = 1
        except Exception as e:
            print(nikkei.columns) # Debug
            print(f"Nikkei Macro Error: {e}")

        # データ取得
        all_stats = []
        chunk_size = 50
        for i in range(0, len(unique_tickers), chunk_size):
            chunk = unique_tickers[i:i+chunk_size]
            full_df = yf.download(" ".join(chunk), period="6mo", interval="1d", group_by='ticker', progress=False, auto_adjust=True)
            
            for ticker in chunk:
                ticker_df = full_df[ticker] if len(chunk) > 1 else full_df
                res = calculate_metrics(ticker_df)
                if res:
                    all_stats.append({
                        "ticker": ticker, "price": res["price"], "dev": res["dev"], "rsi": res["rsi"], "vol": res["vol_ratio"],
                        "volatility": res["volatility"], "trend": res["trend"], "macd": res["macd"], "bb_pos": res["bb_pos"], "gap": res["gap"]
                    })
            print(f"✅ パトロール中... ({min(i+chunk_size, len(unique_tickers))}/{len(unique_tickers)})")

        primary_hits = [s for s in all_stats if (config.ENTRY_DEV_MIN <= s["dev"] <= config.ENTRY_DEV_MAX) and (config.ENTRY_RSI_MIN <= s["rsi"] <= config.ENTRY_RSI_MAX)]
        
        golden_hits = []
        if primary_hits and os.path.exists("xgb_model.pkl") and os.path.exists("lgbm_model.pkl"):
            try:
                print("🧠 最強の合議制 AI (XGB/LGBM) が選別を開始します...")
                xgb_model = joblib.load("xgb_model.pkl")
                lgbm_model = joblib.load("lgbm_model.pkl")
                
                for s in primary_hits:
                    features_df = pd.DataFrame([{
                        'feat_price': s["price"], 'feat_dev': s["dev"], 'feat_rsi': s["rsi"], 'feat_vol': s["vol"],
                        'feat_volatility': s["volatility"], 'feat_trend': s["trend"], 'feat_dayofweek': now_jst.weekday(),
                        'feat_macd': s["macd"], 'feat_bb_pos': s["bb_pos"], 'feat_gap': s["gap"],
                        'feat_nikkei_trend': n_trend, 'feat_fear_index': n_vol, 'feat_market_phase': n_phase
                    }])
                    prob_xgb = xgb_model.predict_proba(features_df)[0][1]
                    prob_lgbm = lgbm_model.predict_proba(features_df)[0][1]
                    
                    # アンサンブル確率 (平均)
                    avg_prob = (prob_xgb + prob_lgbm) / 2
                    s["win_prob"] = avg_prob * 100
                    
                    # 🔥 85% 以上の確信度のみを認定
                    if avg_prob >= 0.85:
                        print(f"🔥 【真実のダイヤ認定】 ({s['win_prob']:.1f}%): {s['ticker']}")
                        golden_hits.append(s)
                    else:
                        print(f"❌ 却下 ({s['win_prob']:.1f}%): {s['ticker']}")
            except Exception as e:
                print(f"AI Ensemble Error: {e}")
                golden_hits = primary_hits
        
        print(f"📊 統計データ: {len(all_stats)}件 / 一次ヒット: {len(primary_hits)}件 / AI合格: {len(golden_hits)}件")
        top_movers = sorted(all_stats, key=lambda x: x['dev'], reverse=True)[:5]

        # 履歴記録 (検証用)
        if golden_hits:
            file_exists = os.path.exists("trade_tracker.csv")
            log_df = pd.DataFrame([{
                "timestamp": now_jst.strftime('%Y-%m-%d %H:%M'),
                "ticker": s["ticker"],
                "entry_price": s["price"],
                "win_prob": s["win_prob"],
                "dev": s["dev"],
                "rsi": s["rsi"],
                "ichimoku": 0.0,
                "vol_trend": 0.0,
                "label": None
            } for s in golden_hits])
            log_df.to_csv("trade_tracker.csv", mode='a', header=not file_exists, index=False, encoding="utf-8")
            print(f"📖 {len(golden_hits)}件の予測を trade_tracker.csv に記録しました。")
            
        # ライブ・ダッシュボードを自動更新 (ヒットがなくても生存確認のために更新)
        try:
            from dashboard_generator import generate_dashboard
            generate_dashboard(last_sync_time=now_jst.strftime('%m/%d %H:%M'))
            print(f"✨ ライブ追跡ボードを更新しました (最終確認: {now_jst.strftime('%H:%M')})")
        except Exception as e:
            print(f"Dashboard Update Error: {e}")

        # Discord通知
        if "http" in webhook_url:
            fields = []
            if golden_hits:
                # 確信度が高い順に並び替え
                golden_hits = sorted(golden_hits, key=lambda x: x['win_prob'], reverse=True)
                hits_text = "".join([f"⭐ **{s['ticker']}**: {s['price']:,.0f}円 (AI確信度:**{s['win_prob']:.1f}%** 🎯)\n" for s in golden_hits[:15]])
                fields.append({"name": f"🔥 【AI精鋭チーム認定：絶対お宝銘柄 ({len(golden_hits)}件)】", "value": hits_text, "inline": False})
            else:
                fields.append({"name": "🛰️ マーケット状況", "value": "現在、AIが『絶対の自信』を持って推奨できる銘柄は見つかりませんでした。無理なトレードは控えましょう。", "inline": False})

            embed = {
                "title": "🛡️ 【AI 資産防衛：1.0% 着実パトロール】",
                "color": 0x00FF88 if golden_hits else 0x3498DB,
                "description": f"解析時刻: {now_jst.strftime('%m/%d %H:%M')}\n500銘柄を調査。水増しなしの生スコア 85% 超えの『真実のダイヤ』を捜索中。",
                "fields": fields,
                "footer": {"text": f"目標利益: {config.EXIT_PROFIT_TARGET}% / 損切: {config.EXIT_STOP_LOSS}% / 監視銘柄数: 500"}
            }
            requests.post(webhook_url, json={"embeds": [embed]})

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_trainer_scan()
