import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import joblib
import os

# --- V20.0: Neural Predator Trainer ---
# 役割: 生成された556件の文脈データから、物理フィルター内の「勝率の差」を学習。

def train_v20_model():
    print("[*] Training V20.0 Neural Context Engine...")
    
    if not os.path.exists("v20_train_data.csv"):
        print("[ERROR] Training data not found.")
        return
        
    df = pd.DataFrame(pd.read_csv("v20_train_data.csv"))
    
    # 特徴量とラベルの分離
    features = ["pb_ratio", "surge_ratio", "volatility", "ma_slope", "rsi", "vol_spike"]
    X = df[features]
    y = df["label"]
    
    # 訓練・テスト分割
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # LightGBM モデル設定 (極めてタイトな過学習防止設定)
    params = {
        "objective": "binary",
        "metric": "auc",
        "verbosity": -1,
        "boosting_type": "gbdt",
        "num_leaves": 8,          # 木を小さく
        "max_depth": 3,           # 浅く
        "learning_rate": 0.05,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "min_child_samples": 20,  # 1つの葉に最低20サンプル
        "seed": 42
    }
    
    train_data = lgb.Dataset(X_train, label=y_train)
    model = lgb.train(params, train_data, num_boost_round=100)
    
    # 評価
    y_pred = model.predict(X_test)
    auc = roc_auc_score(y_test, y_pred)
    
    print("\n" + "="*40)
    print("V20.0 NEURAL CONTEXT REPORT")
    print("="*40)
    print(f"Test AUC Score : {auc:.4f}")
    print(f"Base Win Rate  : {y.mean()*100:.2f}%")
    
    # 特徴量重要度
    importance = pd.DataFrame({'feature': features, 'importance': model.feature_importance()})
    print("\n--- Feature Importance ---")
    print(importance.sort_values(by='importance', ascending=False))
    
    # モデル保存
    if not os.path.exists("models"): os.makedirs("models")
    joblib.dump(model, "models/v20_context_model.pkl")
    print("\n[*] Model saved to 'models/v20_context_model.pkl'")
    print("="*40)

if __name__ == "__main__":
    train_v20_model()
