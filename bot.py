import yfinance as yf
import pandas as pd
import time
from datetime import datetime
from core import TICKER_LIST, get_indicators, load_weights, calculate_score, setup_terminal

# --- 🏹 Sniper AI: Scoring Engine (V1) ---
# 歴史的検証に基づいたロジックを core.py に集約し、シンプルかつ堅牢に進化したスキャナー。

def fetch_market_data():
    """地合い判定 (日経225の200日線)"""
    try:
        n225 = yf.download("^N225", period="1y", progress=False)
        if isinstance(n225.columns, pd.MultiIndex): n225.columns = n225.columns.get_level_values(0)
        n225_ma200 = n225['Close'].rolling(200).mean().iloc[-1]
        n225_curr = n225['Close'].iloc[-1]
        is_bull = n225_curr > n225_ma200
        return is_bull, n225_curr, n225_ma200
    except:
        return True, 0, 0

def main():
    setup_terminal()
    weights_all = load_weights()
    is_bull, n225_curr, n225_ma200 = fetch_market_data()
    regime = "BULL" if is_bull else "BEAR"
    weights = weights_all["regime_bull"] if is_bull else weights_all["regime_bear"]

    print(f"🏹 Sniper AI: Systems Online. (Bulk Scanning Mode)")
    print(f"Market Status: {'📈 BULL' if is_bull else '📉 BEAR'} (Nikkei: {n225_curr:,.0f} / MA200: {n225_ma200:,.0f})")

    # 🌍 一括ダウンロード (1分足: リアルタイム用 & 日足: 指標計算用)
    print(f"📥 Fetching bulk market intelligence...")
    all_now = yf.download(TICKER_LIST, period="1d", interval="1m", progress=False, group_by='ticker')
    all_hist = yf.download(TICKER_LIST, period="3mo", interval="1d", progress=False, group_by='ticker')

    results = []
    for ticker in TICKER_LIST:
        try:
            # ヒストリカルデータの抽出
            if ticker not in all_hist.columns.levels[0]: continue
            df = all_hist[ticker].copy().dropna()
            if df.empty or len(df) < 30: continue
            
            # リアルタイム価格の抽出 (最新の1分足)
            if ticker not in all_now.columns.levels[0]: continue
            df_now = all_now[ticker].copy().dropna()
            if not df_now.empty:
                latest_price = df_now['Close'].iloc[-1]
                # 指標計算用に最後の一行を最新値に更新 (暫定的な調整)
                df.iloc[-1, df.columns.get_loc('Close')] = latest_price
            
            df = get_indicators(df)
            row = df.iloc[-1]
            curr_price = round(row['Close'].item(), 1)
            
            # 共通ロジックでスコア計算
            score = calculate_score(ticker, row, weights, regime)
            
            # 星の数に変換
            stars = "⭐" * (1 if score < 40 else 2 if score < 55 else 3 if score < 70 else 4 if score < 85 else 5)
            
            results.append({
                "ticker": ticker,
                "name": ticker,
                "price": curr_price,
                "rsi": round(row['rsi'].item(), 1),
                "kairi": round(row['kairi'].item(), 1),
                "sigma": round(row['sigma'].item(), 2),
                "score": score,
                "stars": stars,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            print(f"Scanned {ticker}: Price={curr_price} Score={score}")
        except Exception as e:
            # print(f"Skipping {ticker} due to error: {e}")
            pass

    # 保存
    out_df = pd.DataFrame(results).sort_values(by="score", ascending=False)
    out_df.to_csv("database.csv", index=False, encoding='utf-8-sig')
    print(f"🏹 Scan Complete. Results saved to database.csv")

if __name__ == "__main__":
    main()
