import pandas as pd
import numpy as np
import yfinance as yf
from core import TICKER_LIST, SniperCoreV42
from datetime import datetime

def analyze_ml_quality():
    print(f"[*] Starting ML Quality Check (Past 5 days)...")
    core = SniperCoreV42()
    
    # 5日間の5分足データを取得
    data = yf.download(TICKER_LIST, period="5d", interval="5m", group_by='ticker', progress=False)
    
    results = []
    for ticker in TICKER_LIST:
        ticker_data = data[ticker]
        for i in range(50, len(ticker_data)-1):
            try:
                slice_df = ticker_data.iloc[i-50:i]
                if slice_df.isnull().values.any(): continue
                
                # 現在の予測
                pred_res = core.predict_v42(ticker, slice_df)
                
                # 未来（5分後）の実際のリターン
                future_ret = (ticker_data['Close'].iloc[i+1] / ticker_data['Close'].iloc[i]) - 1
                
                results.append({
                    "ticker": ticker,
                    "pred_return": pred_res["pred_return"],
                    "confidence": pred_res["confidence"],
                    "actual_return": future_ret
                })
            except: continue
            
    if not results:
        print("No valid samples found.")
        return

    df = pd.DataFrame(results)
    
    # 相関分析
    corr = df["pred_return"].corr(df["actual_return"])
    
    print("\n" + "="*40)
    print("🧠 ML BRAIN QUALITY REPORT")
    print("="*40)
    print(f"Total Samples    : {len(df)}")
    print(f"Correlation      : {corr:.4f}")
    
    # 上位10%の予測リターンの実力
    q90 = df["pred_return"].quantile(0.9)
    top_ml = df[df["pred_return"] >= q90]
    
    print(f"\n--- Top 10% Pred Return ---")
    print(f"Mean Actual Ret  : {top_ml['actual_return'].mean()*100:.4f}%")
    print(f"Win Rate         : {(top_ml['actual_return'] > 0).mean()*100:.2f}%")
    
    print("\n--- Correlation by Confidence ---")
    df['conf_q'] = pd.qcut(df['confidence'], 4, labels=['Q1', 'Q2', 'Q3', 'Q4'])
    print(df.groupby('conf_q', observed=True)['pred_return'].corr(df['actual_return']))
    print("="*40)

if __name__ == "__main__":
    analyze_ml_quality()
