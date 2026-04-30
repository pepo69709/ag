import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
import os
from sklearn.model_selection import train_test_split

# --- V23.0: ML Brake Trainer ---
# 役割: 物理フィルターをクリアした銘柄の中から「負けやすい状況」を学習。
# 目的: 「アクセル」ではなく、危険を検知して止める「ブレーキ」を構築。

def train_brake_model():
    print("[*] Training V23.0 ML Emergency Brake...")
    
    # 以前生成した v20_train_data.csv (物理通過済みデータ) を活用
    if not os.path.exists("v20_train_data.csv"): return
    df = pd.read_csv("v20_train_data.csv")
    
    # ラベルを反転: 負け(label=0)を 1 (Risk) とする
    df["risk_label"] = 1 - df["label"]
    
    features = ["pb_ratio", "surge_ratio", "volatility", "ma_slope", "rsi", "vol_spike"]
    X = df[features]
    y = df["risk_label"]
    
    # モデル訓練 (リスク検知に特化)
    # 偽陽性(チャンスを逃す)は許容し、偽陰性(リスクを見逃す)を減らす設定
    params = {
        "objective": "binary",
        "metric": "binary_logloss",
        "verbosity": -1,
        "num_leaves": 5,
        "max_depth": 2,
        "learning_rate": 0.05,
        "scale_pos_weight": 1.5, # リスク(負け)の重みを少し上げる
        "seed": 42
    }
    
    train_data = lgb.Dataset(X, label=y)
    model = lgb.train(params, train_data, num_boost_round=50)
    
    if not os.path.exists("models"): os.makedirs("models")
    joblib.dump(model, "models/v23_emergency_brake.pkl")
    print("[*] Emergency Brake Model saved to 'models/v23_emergency_brake.pkl'")

if __name__ == "__main__":
    train_brake_model()
