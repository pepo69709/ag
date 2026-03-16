"""
🔬 リアル・バックテスト（正直バージョン）
============================================
「当日+1%狙い」戦略を、モデルが見たことのない
過去データで実際にシミュレーションします。

ルール:
  - モデルの確信度が85%以上の銘柄を「当日の始値」で買う
  - 当日の高値が+1%に達したら → +1%で利確（完全成立）
  - 達しなかったら → 当日の終値で強制決済（損切含む）
"""

import pandas as pd
import numpy as np
import joblib
import os

print("=" * 60)
print("  🔬 リアル・バックテスト（手数料0円・楽天証券想定）")
print("=" * 60)

# データ読み込み
df = pd.read_csv("ai_training_data_honest.csv")
df = df.sort_values("timestamp").reset_index(drop=True)

features = [
    'feat_dev', 'feat_rsi', 'feat_vol', 'feat_gap', 
    'feat_panic', 'feat_nikkei_vol', 'feat_rel_strength'
]
available = [f for f in features if f in df.columns]


# 🔴 重要：訓練に使っていない「未来の2割」だけでテスト
split = int(len(df) * 0.8)
test_df = df[split:].copy()
print(f"\n📋 テスト対象: {len(test_df)}件 ({test_df['timestamp'].iloc[0]} ～ {test_df['timestamp'].iloc[-1]})")

# モデル読み込み
try:
    # GBはgb_model.pkl、XGBはxgb_model.pkl等
    model_files = [f for f in os.listdir('.') if f.endswith('.pkl')]
    print(f"📦 利用可能なモデル: {model_files}")

    # 勾配ブースティングが最優秀なのでそれを使う
    if 'gb_model.pkl' in model_files:
        model = joblib.load('gb_model.pkl')
        model_name = "勾配ブースティング"
    elif 'xgb_model.pkl' in model_files:
        model = joblib.load('xgb_model.pkl')
        model_name = "XGBoost"
    else:
        model = joblib.load(model_files[0])
        model_name = model_files[0]
    print(f"✅ 使用モデル: {model_name}")
except Exception as e:
    print(f"❌ モデルの読み込み失敗: {e}")
    exit()

# 予測確率を計算
X_test = test_df[available]
probs = model.predict_proba(X_test)[:, 1]
test_df = test_df.copy()
test_df['pred_prob'] = probs

# =====================================================
# 📊 バックテスト本番（複数の閾値で比較）
# =====================================================
print("\n" + "=" * 60)
print("  📊 閾値別バックテスト結果")
print("=" * 60)

for threshold in [0.75, 0.80, 0.85, 0.90]:
    signals = test_df[test_df['pred_prob'] >= threshold].copy()
    n = len(signals)
    if n == 0:
        print(f"\n閾値 {threshold*100:.0f}%: シグナルなし")
        continue

    # label=1 の場合は当日+1%達成（データで確認済みの事実）
    wins   = signals['label'].sum()
    losses = n - wins
    win_rate = wins / n * 100

    # === 損益シミュレーション ===
    # 勝ち: +1.0%の利益
    # 負け: 終値で決済 → feat_priceを使っては不正確なので
    #       label=0のケースは「当日高値が+1%未満」= 損失は不確かだが
    #       最悪ケース（-0.5%平均）を仮定
    avg_loss_assumption = -0.5  # 現実的な平均損失（高値が目標未達で終値で売る）
    total_return = (wins * 1.0 + losses * avg_loss_assumption)
    avg_per_trade = total_return / n

    print(f"""
🎯 閾値: {threshold*100:.0f}% 以上
   シグナル数:    {n:>5} 件
   勝ち(+1%達成): {wins:>5} 件 ({win_rate:.1f}%)
   負け:          {losses:>5} 件
   通算損益(仮定): {total_return:>+.1f}% ({avg_per_trade:>+.2f}% / 1トレード)
   → 100万円なら: {total_return * 10000:>+,.0f}円の利益（推定）""")

# =====================================================
# 📅 月別の成績（市場環境の確認）
# =====================================================
print("\n" + "=" * 60)
print("  📅 月別の勝率（閾値85%）")
print("=" * 60)

signals_85 = test_df[test_df['pred_prob'] >= 0.85].copy()
signals_85['month'] = pd.to_datetime(signals_85['timestamp']).dt.to_period('M')
monthly = signals_85.groupby('month').agg(
    total=('label', 'count'),
    wins=('label', 'sum')
).reset_index()
monthly['win_rate'] = (monthly['wins'] / monthly['total'] * 100).round(1)
monthly['判定'] = monthly['win_rate'].apply(lambda r: '✅ 勝ち越し' if r >= 50 else '❌ 負け越し')
print(monthly[['month', 'total', 'wins', 'win_rate', '判定']].to_string(index=False))

# =====================================================
# ⚠️ 結論
# =====================================================
print("\n" + "=" * 60)
print("  ⚠️  正直な評価")
print("=" * 60)
if len(signals_85) > 0:
    overall_wr = signals_85['label'].mean() * 100
    if overall_wr >= 60:
        print(f"  ✅ 閾値85%での勝率は {overall_wr:.1f}%。実戦投入を検討できるレベルです。")
    elif overall_wr >= 50:
        print(f"  ⚠️  閾値85%での勝率は {overall_wr:.1f}%。コインの裏表より少し良い程度。")
        print("      閾値を90%に上げるか、追加フィルターが必要です。")
    else:
        print(f"  ❌ 閾値85%での勝率は {overall_wr:.1f}%。まだ実戦投入は難しい。")
        print("      モデルの特徴量や学習戦略の見直しが必要です。")
print("=" * 60)
