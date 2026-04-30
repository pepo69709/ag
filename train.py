import yfinance as yf
import pandas as pd
import numpy as np
import os
import pickle
from datetime import datetime
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from core import TICKER_LIST, Indicators, setup_terminal, get_market_regime

# --- 🏋️ Sniper AI V9.1: Universal Trainer ---

def train_model():
    setup_terminal()
    print("Sniper AI V9.1 [TRAINER]: Learning latest market patterns...")

    # データ取得
    all_data = yf.download(TICKER_LIST[:20], period="2y", interval="1d", progress=False, group_by='ticker')
    
    X, y_reg, y_clf = [], [], []
    
    for ticker in TICKER_LIST[:20]:
        try:
            df = all_data[ticker].copy().dropna()
            if len(df) < 100: continue
            
            # 特徴量エンジニアリング (V4.0 indicators使用)
            df['rsi'] = Indicators.rsi(df)
            df['atr'] = Indicators.atr(df)
            df['vol_spike'] = Indicators.volume_spike(df)
            df['target'] = df['Close'].pct_change(5).shift(-5) # 5日後のリターン
            
            df = df.dropna()
            for i in range(len(df)):
                row = [df['rsi'].iloc[i], df['atr'].iloc[i], df['vol_spike'].iloc[i]]
                X.append(row)
                y_reg.append(df['target'].iloc[i])
                y_clf.append(1 if df['target'].iloc[i] > 0.02 else 0)
                
        except: continue

    X = np.array(X)
    y_reg = np.array(y_reg)
    y_clf = np.array(y_clf)

    print(f"Training on {len(X)} samples...")

    # 1. 回帰モデル (LGBM風 & Ridge)
    model_lgbm = HistGradientBoostingRegressor().fit(X, y_reg)
    model_ridge = Ridge().fit(X, y_reg)
    
    # 2. 分類モデル (勝率用)
    base_clf = RandomForestClassifier(n_estimators=50)
    calibrated_clf = CalibratedClassifierCV(base_clf, cv=3).fit(X, y_clf)

    # 保存
    os.makedirs("models", exist_ok=True)
    with open("models/model_lgbm.pkl", "wb") as f: pickle.dump(model_lgbm, f)
    with open("models/model_ridge.pkl", "wb") as f: pickle.dump(model_ridge, f)
    with open("models/model_clf.pkl", "wb") as f: pickle.dump(calibrated_clf, f)

    print("Success: New AI Models deployed to /models/")

if __name__ == "__main__":
    train_model()
