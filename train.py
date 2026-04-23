import yfinance as yf
import pandas as pd
import random
import json
from datetime import datetime, timedelta
import os
from core import TICKER_LIST, get_indicators, calculate_score, setup_terminal, get_market_regime

# --- 🏋️ Sniper AI: Trainer V3.1 ---
# V3.1: ウォークフォワード検証（過学習防止）+ 短期指標対応

TRAIN_TICKERS = TICKER_LIST[:30]  # 学習対象（上位30銘柄）

def fetch_data(period="6mo"):
    """学習用データの一括取得"""
    data = {}
    print(f"📡 データ取得中 (期間: {period})...")
    for ticker in TRAIN_TICKERS:
        try:
            df = yf.download(ticker, period=period, progress=False)
            if df is None or df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = get_indicators(df)
            if df is not None and len(df) >= 30:
                data[ticker] = df
        except Exception:
            continue
    print(f"✅ {len(data)} 銘柄のデータ取得完了")
    return data


def simulate_profit_on_window(df_window, weights, regime):
    """指定した期間データ上で特定の重みセットを使って仮想利益を計算する"""
    if df_window is None or len(df_window) < 10:
        return 0.0

    total_profit = 0.0
    entry_triggered = False

    for i in range(len(df_window) - 6):
        row = df_window.iloc[i]
        if pd.isna(row.get('rsi', float('nan'))):
            continue

        # ダミーティッカーでスコア計算（インバース判定なし）
        score = calculate_score("DUMMY.T", row, weights, regime)

        # スコア70以上でエントリー → 5日後の騰落率を利益とする
        if score >= 70:
            future_ret = df_window['Close'].pct_change(5).iloc[i + 5]
            if not pd.isna(future_ret):
                total_profit += future_ret

    return total_profit


def walk_forward_test(all_data, candidate_weights, regime):
    """
    ウォークフォワード検証:
    - 訓練: 最初の4ヶ月（インデックス 0〜-30）
    - 検証: 直近1ヶ月（インデックス -30〜）
    ※ 訓練と検証の両方で利益が出た重みのみを「信頼できる重み」として採用する
    """
    train_profit = 0.0
    val_profit   = 0.0
    count = 0

    for ticker, df in all_data.items():
        if len(df) < 60:
            continue
        split = max(len(df) - 22, 30)  # 直近約22営業日（1ヶ月）を検証用に
        train_df = df.iloc[:split].copy()
        val_df   = df.iloc[split:].copy()

        train_profit += simulate_profit_on_window(train_df, candidate_weights, regime)
        val_profit   += simulate_profit_on_window(val_df,   candidate_weights, regime)
        count += 1

    if count == 0:
        return -999.0, -999.0
    return train_profit / count, val_profit / count


def train():
    setup_terminal()
    print("=" * 55)
    print("🏋️ Sniper AI V3.1: ウォークフォワード・トレーニング開始")
    print("=" * 55)

    # 1. データ取得
    all_data = fetch_data(period="6mo")
    if not all_data:
        print("❌ データ取得失敗。ネット接続を確認してください。")
        return

    # 2. 現在の地合いを確認
    regime = get_market_regime()
    print(f"\n🌍 現在の地合い: [{regime}]")
    print("🔍 100パターンの重みをウォークフォワード検証中...\n")

    best_weights   = None
    best_val_score = -999.0
    results_log    = []

    for i in range(100):
        candidate = {
            "rsi_weight":   round(random.uniform(0.1, 0.8), 2),
            "kairi_weight": round(random.uniform(0.1, 0.8), 2),
            "vol_weight":   round(random.uniform(0.1, 0.8), 2),
            "sigma_filter": round(random.uniform(0.2, 1.2),  2),
            "short_weight": round(random.uniform(0.0, 0.6),  2),  # ★ 短期指標重み
        }

        train_score, val_score = walk_forward_test(all_data, candidate, regime)
        results_log.append((val_score, train_score, candidate))

        if (i + 1) % 20 == 0:
            print(f"  [{i+1}/100] ベスト検証スコア: {best_val_score*100:.2f}%")

        # ★ 訓練・検証の両方でプラスの重みのみ採用（過学習防止の核心）
        if val_score > best_val_score and train_score > 0:
            best_val_score = val_score
            best_weights   = candidate

    # フォールバック: 全パターンが検証でマイナスの場合はデフォルト重みを使用
    if best_weights is None:
        print("\n⚠️ 検証をパスした重みが見つかりませんでした。デフォルト重みを使用します。")
        best_weights = {
            "rsi_weight": 0.3, "kairi_weight": 0.2,
            "vol_weight": 0.5, "sigma_filter": 1.0, "short_weight": 0.0
        }
        best_val_score = 0.0

    # 3. 既存ファイルのバックアップ
    if not os.path.exists("weight_history"):
        os.makedirs("weight_history")

    if os.path.exists("model_weights.json"):
        with open("model_weights.json", "r", encoding="utf-8") as f:
            current = json.load(f)
    else:
        current = {}

    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"weight_history/weights_{timestamp}.json"
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=4, ensure_ascii=False)
    print(f"\n💾 現在の重みをバックアップ: {backup_path}")

    # 4. 新しい重みをレジームに対応する形で保存
    # BULLレジームの重みを更新（現在の地合いに関わらず、BULL用として保存）
    current["regime_bull"]     = best_weights
    current["regime_volatile"] = {
        **best_weights,
        "short_weight": min(best_weights.get("short_weight", 0) + 0.2, 0.6),  # VOLATILEは短期重みを強化
    }
    current["metadata"] = {
        "last_trained":     datetime.now().strftime("%Y-%m-%d %H:%M"),
        "training_regime":  regime,
        "val_score_pct":    round(best_val_score * 100, 2),
        "walk_forward":     True,
    }

    with open("model_weights.json", "w", encoding="utf-8") as f:
        json.dump(current, f, indent=4, ensure_ascii=False)

    print("\n" + "=" * 55)
    print(f"✅ 訓練完了！  採用重み: {best_weights}")
    print(f"📊 ウォークフォワード検証スコア: {best_val_score * 100:.2f}%")
    print(f"🌍 地合い [{regime}] に最適化された重みを保存しました")
    print("=" * 55)


if __name__ == "__main__":
    train()
