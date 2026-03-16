import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score
import joblib
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

# ==========================================
# 🧠 AI-TRAINER: プロフェッショナル仕様
# ==========================================

print("🤖 プロフェッショナル・モードで学習を開始します...")

file_path = "ai_training_data_honest.csv"
try:
    df = pd.read_csv(file_path)
    df = df.sort_values("timestamp").reset_index(drop=True)
except FileNotFoundError:
    print("❌ データが見つかりません。")
    exit()

# 特徴量リスト（正直バージョン）
features = [
    'feat_dev', 'feat_rsi', 'feat_vol', 'feat_gap', 
    'feat_panic', 'feat_nikkei_vol', 'feat_rel_strength'
]

available_features = [f for f in features if f in df.columns]
X = df[available_features]
y = df['label']

# 🔴 重要: 時系列分割 (カンニング防止)
# シャッフルせず、過去から未来への流れを保ったまま 8:2 で分ける
split = int(len(df) * 0.8)
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

print(f"✅ 学習データ: {len(X_train)}件 / テストデータ(未来分): {len(X_test)}件\n")

# クラスの不均衡を計算 (XGBoost/LightGBM用)
scale = len(y_train[y_train==0]) / max(len(y_train[y_train==1]), 1)

models = {
    "勾配ブースティング (Gradient Boosting)": GradientBoostingClassifier(n_estimators=200, max_depth=4, learning_rate=0.05, random_state=42),
    "⭐ XGBoost": XGBClassifier(n_estimators=300, max_depth=5, learning_rate=0.03, scale_pos_weight=scale, eval_metric='logloss', random_state=42),
    # --- 🔹 LightGBM（高確約モード） ---
    "⭐ LightGBM": LGBMClassifier(
        n_estimators=300,
        learning_rate=0.1,  # 少し学習を強める
        num_leaves=63,      # より複雑なパターンを捉える
        importance_type='gain',
        scale_pos_weight=scale, # Keep class imbalance handling
        random_state=42,
        verbose=-1
    ),
}

best_precision = 0
best_model = None
best_name = ""

print("🏆 【時系列バリデーション・選手権】")
print("-" * 50)

for name, model in models.items():
    model.fit(X_train, y_train)
    
    # 🔴 予測確率計算
    y_prob = model.predict_proba(X_test)[:, 1]
    
    # 指きり値（しきいち）を高めに設定 (例: 70% 以上の確信がある時だけ買う)
    threshold = 0.65
    y_pred = (y_prob >= threshold).astype(int)
    
    # 指標計算
    total_signals = np.sum(y_pred)
    if total_signals == 0:
        precision = 0
    else:
        precision = precision_score(y_test, y_pred, zero_division=0)
    
    accuracy = accuracy_score(y_test, y_pred)
    
    # 期待値計算 (利益10%, 損失3% の簡易シミュレーション)
    # 期待値 = (勝率 × 10) - (負け率 × 3)
    exp_value = (precision * 10.0) - ((1 - precision) * 3.0) if total_signals > 0 else -3.0

    print(f"🔹 {name}")
    print(f"   🎯 確信度{int(threshold*100)}%以上の精度: {precision*100:.1f}%")
    print(f"   📊 検知回数 (未来2割中): {total_signals}回 / {len(X_test)}日分")
    print(f"   💰 1トレード期待値: +{exp_value:.2f}%")
    print("-" * 40)
    
    if precision > best_precision:
        best_precision = precision
        best_model = model
        best_name = name

if best_model:
    print(f"\n👑 最優秀モデル: {best_name}")
    # 全モデルを保存 (アンサンブル用)
    joblib.dump(models["勾配ブースティング (Gradient Boosting)"], "gb_model.pkl")
    joblib.dump(models["⭐ XGBoost"], "xgb_model.pkl")
    joblib.dump(models["⭐ LightGBM"], "lgbm_model.pkl")
    # 互換性のためのメイン保存
    joblib.dump(best_model, "trained_ai_model.pkl")
    print(f"👑 最優秀モデル: {best_name}")
    print("💾 確率予測対応モデルを保存しました！ (全モデル保存完了)")
