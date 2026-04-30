import pandas as pd
import lightgbm as lgb
from sklearn.linear_model import Ridge
from sklearn.model_selection import TimeSeriesSplit
from sklearn.calibration import CalibratedClassifierCV
import joblib
import os

# --- 🧠 Sniper AI V6.4: Ensemble & Conviction Trainer ---
# 役割: 勾配ブースティング(LGBM)と線形モデル(Ridge)を組み合わせ、予測の「ブレ」を捉える。

class ModelTrainerV64:
    def __init__(self, data_path="training_data_v4.csv"):
        self.data_path = data_path

    def train(self):
        if not os.path.exists(self.data_path): return
        df = pd.read_csv(self.data_path)
        
        X = df.drop(columns=['ticker', 'target_return', 'Date'])
        y_reg = df['target_return']
        y_clf = (df['target_return'] > 0.003).astype(int) 

        # 時系列分割
        split_idx = int(len(df) * 0.8)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_reg_train, y_reg_test = y_reg.iloc[:split_idx], y_reg.iloc[split_idx:]
        y_clf_train, y_clf_test = y_clf.iloc[:split_idx], y_clf.iloc[split_idx:]

        # 1. メインモデル (LightGBM)
        print("Training Main Model (LGBM)...")
        tscv = TimeSeriesSplit(n_splits=5)
        base_clf = lgb.LGBMClassifier(n_estimators=1000, learning_rate=0.02, max_depth=5, verbosity=-1)
        calibrated_clf = CalibratedClassifierCV(base_clf, method='isotonic', cv=tscv)
        calibrated_clf.fit(X_train, y_clf_train)
        
        # 2. セカンドモデル (Ridge Regressor) - 線形な視点
        # LGBMが見逃す「単純なトレンド」や「外れ値」を捉えるための線形モデル
        print("Training Second Model (Ridge)...")
        ridge_model = Ridge(alpha=1.0)
        ridge_model.fit(X_train.fillna(0), y_reg_train)

        # 保存
        joblib.dump(calibrated_clf, "sniper_v4_clf_calibrated.pkl")
        joblib.dump(ridge_model, "sniper_v4_ridge_reg.pkl")
        joblib.dump(X.columns.tolist(), "feature_columns.pkl")
        print("--- V6.4 Ensemble Models Saved ---")

if __name__ == "__main__":
    trainer = ModelTrainerV64()
    trainer.train()
