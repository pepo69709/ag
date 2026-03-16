import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import precision_score
import os

print("🚀 【未知の領域】完全未踏期間ブラインドテストを開始します...")

# 1. 保存された数学モデルをロード
try:
    model = joblib.load('trained_ai_model.pkl')
    print("✅ 数学モデルのロード完了")
except:
    print("❌ モデルが見つかりません。先に学習を行ってください。")
    exit()

# 2. データをロード（全期間）
try:
    df = pd.read_csv("ai_training_data_math.csv").sort_values("timestamp").reset_index(drop=True)
    print(f"📊 全データ件数: {len(df)}")
except:
    print("❌ データファイルが見つかりません。")
    exit()

# 特徴量リスト
features = ['feat_zscore', 'feat_dev_adj', 'feat_vscore', 'feat_rsi', 'feat_rsi_diff', 'feat_gap', 'feat_market_ret', 'feat_market_vol']

# 3. 未知の期間（最新の10%）を切り出す
# 過去8割で学習し、その後の2割（テスト用）があったが、
# 今回はさらにその中でも「モデルが今回初めて触れる最新の期間」に絞る
unseen_start_idx = int(len(df) * 0.90) 
unseen_df = df[unseen_start_idx:].copy()

print(f"📅 未知のテスト期間: {unseen_df['timestamp'].iloc[0]} ～ {unseen_df['timestamp'].iloc[-1]}")
print(f"📋 検証データ件数: {len(unseen_df)} 件")

# 4. 予測の実行
X_unseen = unseen_df[features]
y_unseen = unseen_df['label']
probs = model.predict_proba(X_unseen)[:, 1]

# 5. スコア集計
baseline = y_unseen.mean() * 100

# 確信度 85% 以上でのシミュレーション
threshold = 0.85
signals = (probs >= threshold)
n_signals = np.sum(signals)

print("\n" + "="*50)
print(f"   🏆 ブラインドテスト結果 (未知の10%期間)   ")
print("="*50)
print(f"📉 戦略なし（全部買った場合）の勝率: {baseline:.1f}%")

if n_signals > 0:
    # 実際の勝率
    final_win_rate = precision_score(y_unseen[signals], [1]*n_signals, zero_division=0)
    
    print(f"🎯 AIが『激熱』と判断した回数: {n_signals}回")
    print(f"🔥 その時の実際の勝率: {final_win_rate*100:.1f}%")
    
    # 利益シミュレーション（1トレード1%利確想定）
    # 負けトレードは現実的に当日の終値引け、あるいは最悪ケース -1.0% と仮定
    total_prof = (n_signals * final_win_rate * 1.0) + (n_signals * (1 - final_win_rate) * -1.0)
    
    print(f"💰 この期間の推定利回り: {total_prof:+.2f}%")
    
    if final_win_rate > 0.70:
        print("\n✅ 結論: 未知の期間でも7割以上の勝率を維持。実戦投入可能な『本物』の数式です。")
    else:
        print("\n⚠️ 結論: 勝率が低下。相場の質が変わった可能性があります。再調整が必要です。")
else:
    print("🤖 AI判定: 『この期間、数学的に勝てると確信できるチャンスは一度もなかったのだ。これが最強の守備なのだ』")

print("="*50)
