import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.calibration import CalibratedClassifierCV
import pickle
import os


# --- 🧠 Sniper AI V7.0: 25-Feature Ensemble Trainer ---
# 役割: training_data_v4.csvの25特徴量で訓練し、models/フォルダへ保存する。
# server.pyの predict_ev() と特徴量・保存先を完全に統一する。

FEATURE_COLS = [
    'RSI', 'MACD', 'MACD_Signal',
    'BB_Upper', 'BB_Mid', 'BB_Lower',
    'ATR', 'ADX',
    'SMA_20', 'SMA_50', 'SMA_200',
    'kairi_20', 'kairi_200',
    'vol_ratio',
    'return_lag_1', 'rsi_lag_1',
    'return_lag_2', 'rsi_lag_2',
    'return_lag_3', 'rsi_lag_3',
    'high_52w_ratio', 'roc_20', 'bb_position',
    'atr_compression', 'vol_trend',
    'mkt_trend', 'fx_roc', 'mkt_vol'
]




def train():
    data_path = "training_data_v4.csv"
    if not os.path.exists(data_path):
        print(f"[ERROR] {data_path} が見つかりません。先にデータ収集を実行してください。")
        return

    df = pd.read_csv(data_path)
    print(f"[INFO] データ読込完了: {df.shape}")

    # 特徴量と目標変数を切り出す
    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        print(f"[ERROR] 以下の列が training_data_v4.csv に存在しません: {missing}")
        return

    X = df[FEATURE_COLS].fillna(0)
    y_reg = df['target_return']                          # EV 予測（5日後終値リターン）
    y_clf = df['y_clf']                                  # 正解ラベル（1.0%以上かつ損切り回避）



    # 時系列分割（8:2）
    split_idx = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_reg_train = y_reg.iloc[:split_idx]
    y_clf_train = y_clf.iloc[:split_idx]
    y_clf_test  = y_clf.iloc[split_idx:]

    os.makedirs("models", exist_ok=True)

    # --- モデル1: LightGBM Regressor（EV予測）---
    print("[TRAIN] LightGBM Regressor (EV)...")
    lgbm_reg = lgb.LGBMRegressor(
        n_estimators=500, learning_rate=0.03,
        max_depth=5, num_leaves=31, verbosity=-1
    )
    lgbm_reg.fit(X_train, y_reg_train)
    with open("models/model_lgbm.pkl", "wb") as f:
        pickle.dump(lgbm_reg, f)
    print("[SAVED] models/model_lgbm.pkl")

    # --- モデル2: LightGBM Classifier（True/False判定）---
    print("[TRAIN] LightGBM Classifier (Win/Loss)...")
    tscv = TimeSeriesSplit(n_splits=5)
    base_clf = lgb.LGBMClassifier(
        n_estimators=500, learning_rate=0.03,
        max_depth=5, num_leaves=31, verbosity=-1
    )
    calibrated_clf = CalibratedClassifierCV(base_clf, method='isotonic', cv=tscv)
    calibrated_clf.fit(X_train, y_clf_train)
    with open("models/model_clf.pkl", "wb") as f:
        pickle.dump(calibrated_clf, f)
    print("[SAVED] models/model_clf.pkl")

    # --- 特徴量リストを保存 ---
    with open("models/feature_cols.pkl", "wb") as f:
        pickle.dump(FEATURE_COLS, f)
    print("[SAVED] models/feature_cols.pkl")

    # --- 評価 ---
    test_preds = calibrated_clf.predict(X_test)
    acc = (test_preds == y_clf_test).mean()
    print(f"\n[RESULT] 分類器テスト精度: {acc:.1%}")
    print("--- V8.0 モデル訓練完了 → models/ に保存済み ---")


if __name__ == "__main__":
    train()
