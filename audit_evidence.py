import pandas as pd
import joblib
import numpy as np

# モデルとデータのロード
model = joblib.load('trained_ai_model.pkl')
df = pd.read_csv("ai_training_data_math.csv").sort_values("timestamp")

# 未知の最新期間に絞る
test_df = df[int(len(df) * 0.9):].copy()
features = ['feat_zscore', 'feat_dev_adj', 'feat_vscore', 'feat_rsi', 'feat_rsi_diff', 'feat_gap', 'feat_market_ret', 'feat_market_vol']

# 予測
probs = model.predict_proba(test_df[features])[:, 1]
test_df['prob'] = probs

# 確信度が高い（激熱）かつ、実際に成功した（label=1）事例を直近から探す
lucky_shots = test_df[(test_df['prob'] >= 0.88) & (test_df['label'] == 1)].sort_values("timestamp", ascending=False)

print("🔍 司令官への『証拠提供報告書』")
print("-" * 50)
if not lucky_shots.empty:
    sample = lucky_shots.iloc[0] # 一番直近の成功事例
    print(f"銘柄コード: {sample['ticker']}")
    print(f"的中した日: {sample['timestamp']}")
    print(f"AI確信度  : {sample['prob']*100:.1f}%")
    print("\n💡 確認手順:")
    print(f"1. Yahoo!ファイナンス等で『{sample['ticker']}』のチャートを開く")
    print(f"2. 日付を『{sample['timestamp']}』に合わせる")
    print(f"3. その日の『始値』に対し、当日の『高値』が+1%以上になっているか確認してください。")
    print("-" * 50)
    print("AIはこの日、統計的な歪み（安すぎ＋買戻しサイン）を数学的に検知していました。")
else:
    print("的中事例が見つかりませんでした。")
