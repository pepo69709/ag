import pandas as pd
import numpy as np
import joblib
from lightgbm import LGBMClassifier
from sklearn.metrics import precision_score
import os

print("🧬 数学モデル（正直版）を特訓中...")

file_path = "ai_training_data_math.csv"
try:
    # 完全に時系列順に並べる
    df = pd.read_csv(file_path).sort_values("timestamp").reset_index(drop=True)
except Exception as e:
    print(f"❌ データ読み込み失敗: {e}")
    exit()

# 数学強化された特徴量リスト
features = [
    'feat_zscore', 'feat_dev_adj', 'feat_vscore', 
    'feat_rsi', 'feat_rsi_diff', 'feat_gap', 
    'feat_market_ret', 'feat_market_vol'
]

X = df[features]
y = df['label']

# 🔴 時系列リーク防止：過去8割で学習、未来2割でテスト
split = int(len(df) * 0.8)
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

print(f"📊 学習件数: {len(X_train)} / テスト件数: {len(X_test)}")

# モデル設定（過学習を抑え、汎化性能を重視）
model = LGBMClassifier(
    n_estimators=300,
    learning_rate=0.05,
    num_leaves=31,
    min_child_samples=100,
    importance_type='gain',
    random_state=42,
    verbose=-1
)

model.fit(X_train, y_train)

# 未来データで精度テスト
y_prob = model.predict_proba(X_test)[:, 1]

# ベースライン（全データで買った場合）
baseline_win_rate = y_test.mean() * 100

# AIが厳選した場合（確信度80%以上で集計）
threshold = 0.80
high_conf = (y_prob >= threshold)
n_signals = np.sum(high_conf)

print(f"\n--- 最終検証（未来データ区間） ---")
print(f"📉 何も考えずに全銘柄買った場合の勝率: {baseline_win_rate:.1f}%")

if n_signals > 0:
    precision = precision_score(y_test[high_conf], [1]*n_signals, zero_division=0)
    print(f"🤖 AIが『確信度{int(threshold*100)}%以上』と判断した時の勝率: {precision*100:.1f}%")
    print(f"📈 チャンス発生回数: {n_signals}回 / 全{len(X_test)}データ中")
    
    # さらに厳しい基準（90%）
    high_conf_90 = (y_prob >= 0.90)
    n_90 = np.sum(high_conf_90)
    if n_90 > 0:
        prec_90 = precision_score(y_test[high_conf_90], [1]*n_90, zero_division=0)
        print(f"🔥 AIが『確信度90%以上』と判断した時の勝率: {prec_90*100:.1f}% (回数: {n_90}回)")
else:
    print("🤖 AI判定: 『この2割の期間、確信を持って買えるチャンスは一度もなかったのだ…』")

joblib.dump(model, "trained_ai_model.pkl")
print("\n💾 数学モデルを保存しました！")
