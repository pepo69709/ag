import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import accuracy_score
import joblib
import os

# --- V21.0: Regime Switch Trainer ---
# 役割: 市場全体の特徴量から、その日の戦略稼働の是非を判定するスイッチを訓練。

def train_regime_switch():
    print("[*] Training V21.0 Regime Switch Engine...")
    
    if not os.path.exists("v21_regime_data.csv"):
        print("[ERROR] Regime data not found.")
        return
        
    df = pd.read_csv("v21_regime_data.csv")
    
    features = ["morning_ret", "market_vol", "ad_ratio"]
    X = df[features]
    y = df["label"]
    
    # 少量データのため Leave-One-Out 交差検証で精度を確認
    loo = LeaveOneOut()
    y_true, y_pred = [], []
    
    for train_index, test_index in loo.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]
        
        clf = RandomForestClassifier(n_estimators=50, max_depth=3, random_state=42)
        clf.fit(X_train, y_train)
        y_true.append(y_test.values[0])
        y_pred.append(clf.predict(X_test)[0])
        
    acc = accuracy_score(y_true, y_pred)
    
    print("\n" + "="*40)
    print("V21.0 REGIME SWITCH REPORT")
    print("="*40)
    print(f"Leave-One-Out Accuracy: {acc:.4f}")
    print(f"Market Win Ratio      : {y.mean()*100:.2f}%")
    
    # 最終モデルを全データで訓練して保存
    final_clf = RandomForestClassifier(n_estimators=50, max_depth=3, random_state=42)
    final_clf.fit(X, y)
    
    if not os.path.exists("models"): os.makedirs("models")
    joblib.dump(final_clf, "models/v21_regime_switch.pkl")
    
    print("\n--- Feature Importance ---")
    for f, imp in zip(features, final_clf.feature_importances_):
        print(f"{f:12}: {imp:.4f}")
        
    print("\n[*] Model saved to 'models/v21_regime_switch.pkl'")
    print("="*40)

if __name__ == "__main__":
    train_regime_switch()
