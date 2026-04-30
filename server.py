from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import os
import json
import glob
from datetime import datetime
import numpy as np
from execution_engine import ExecutionEngine
from core import calculate_v4_score
from execution_engine import ExecutionEngine

# 変更: db_path が未定義だったので load_latest_database() を使用
# visual_confirm の DB 読み込み
# db = pd.read_csv(db_path)  →  db = load_latest_database()
# generate_video_script の DB 読み込み
# db = pd.read_csv(db_path)  →  db = load_latest_database()

# -------------------------------------------------
# CSV ローディングユーティリティ（最新ファイルを自動取得）
# -------------------------------------------------
def load_latest_database():
    # database.csv が存在すればそれを使用
    if os.path.exists("database.csv"):
        return pd.read_csv("database.csv")
    # 無ければ database_*.csv の最新ファイルを取得
    files = sorted(glob.glob("database_*.csv"), key=os.path.getmtime)
    if files:
        return pd.read_csv(files[-1])
    # どちらも無いときは空の DataFrame を返す
    return pd.DataFrame()


app = Flask(__name__, static_folder='.')
CORS(app)

# db_path is no longer used; load_latest_database() will pick the latest file
portfolio_path = "portfolio.json"  # JSON が無い場合は portfolio.csv へフォールバック
positions_file = "positions.json"
log_file = "trade_log.csv"
engine = ExecutionEngine(positions_file, log_file)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

@app.route('/api/record', methods=['POST'])
def record_trade():
    try:
        data = request.json
        # ExecutionEngineの管理下にも追加
        positions = engine.load_positions()
        # 既存チェック
        if not any(p['ticker'] == data['ticker'] for p in positions):
            positions.append({
                "ticker": data['ticker'],
                "entry_price": float(data['price']),
                "entry_date": datetime.now().strftime("%Y-%m-%d"),
                "entry_ev": data.get('true_ev', 0),
                "entry_win_prob": data.get('win_prob', 0),
                "note": data.get('note', "")
            })
            engine.save_positions(positions)
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    # 1. ポートフォリオの読み込み（JSON があればそれ、無ければ CSV）
    if os.path.exists(portfolio_path):
        # JSON が存在する場合はそのままロード
        with open(portfolio_path, "r") as f:
            portfolio = json.load(f)
    elif os.path.exists("portfolio.csv"):
        # CSV がある場合は DataFrame に変換して JSON 形式に整形
        df = pd.read_csv("portfolio.csv")
        portfolio = df.to_dict(orient='records')
    else:
        return jsonify([])

    # 2. 最新価格での Exit 判定（価格は DB から取得）
    db = load_latest_database()
    if not db.empty:
        current_prices = dict(zip(db['ticker'], db['price']))
        engine.check_exits(current_prices)

    # 3. positions.json があればポジション情報と同期し、古い銘柄を除外
    if os.path.exists(positions_file):
        with open(positions_file, "r") as f:
            positions = json.load(f)
        # ポートフォリオに残っていない古いポジションを除外
        portfolio = [p for p in portfolio if any(pos['ticker'] == p['ticker'] for pos in positions)]
        # 同期結果を JSON に書き戻す（次回用に保存）
        with open(portfolio_path, "w") as f:
            json.dump(portfolio, f, indent=4)

    return jsonify(portfolio)

@app.route('/api/performance', methods=['GET'])
def get_performance():
    if not os.path.exists(log_file):
        return jsonify({"ic": 0, "equity": [], "hit_rate": 0, "status": "No Data"})
    
    df = pd.read_csv(log_file)
    if len(df) < 3:
        return jsonify({"ic": 0, "equity": df['pnl_rate'].cumsum().tolist(), "hit_rate": 0, "status": "Gathering Data..."})
    
    # IC (情報係数)
    ic = df['entry_ev'].corr(df['pnl_rate'], method='spearman')
    # 累積利益率
    equity = df['pnl_rate'].cumsum().tolist()
    # ヒット率
    hit_rate = (df['pnl_rate'] > 0).mean()
    
    status = "Healthy" if ic > 0.05 else "Stale" if ic < 0 else "Weak"
    
    return jsonify({
        "ic": round(ic, 3),
        "equity": equity,
        "hit_rate": round(hit_rate * 100, 1),
        "status": status,
        "total_trades": len(df)
    })

@app.route('/api/rebalance', methods=['GET'])
def get_rebalance_advice():
    if not os.path.exists(positions_file):
        return jsonify([])
    db = load_latest_database()
    if db.empty:
        return jsonify([])
    ideal_weights = dict(zip(db['ticker'], db['portfolio_weight']))
    
    with open(positions_file, "r") as f:
        positions = json.load(f)
    
    if not positions: return jsonify([])

    current_prices = dict(zip(db['ticker'], db['price']))
    total_value = 0
    holdings = {}
    
    for p in positions:
        ticker = p['ticker']
        price = current_prices.get(ticker, p['entry_price'])
        qty = p.get('quantity', 100)
        value = price * qty
        holdings[ticker] = {"value": value, "qty": qty}
        total_value += value
        
    advice = []
    for ticker, ideal_w in ideal_weights.items():
        if ideal_w <= 0 and ticker not in holdings: continue
        current_w = holdings.get(ticker, {}).get("value", 0) / total_value if total_value > 0 else 0
        diff_w = ideal_w - current_w
        advice.append({
            "ticker": ticker,
            "ideal_weight": round(ideal_w * 100, 1),
            "current_weight": round(current_w * 100, 1),
            "drift": round(diff_w * 100, 1),
            "action": "BUY" if diff_w > 0.05 else "SELL" if diff_w < -0.05 else "HOLD"
        })
    return jsonify(advice)

@app.route('/api/visual_confirm', methods=['POST'])
def visual_confirm():
    try:
        ticker = request.form.get('ticker')
        file = request.files.get('image')
        if not file:
            return jsonify({"status": "error", "message": "No image uploaded"}), 400

        # --- 📸 V8.0: AI Vision Pipeline (Simulated) ---
        # 実際にはここで画像をGemini Vision API等に送り、価格やトレンドを読み取る
        # 今回はデモとして、最新のyfinance価格に近いランダムな数値を「画像から読み取った値」とする
        
        db = load_latest_database()
        row = db[db['ticker'] == ticker]
        if row.empty:
            return jsonify({"status": "error", "message": "Ticker not found"}), 404
        
        yf_price = float(row.iloc[0]['price'])
        # 画像から読み取ったと仮定する現在値（±1%の範囲でランダムに変動）
        simulated_realtime_price = round(yf_price * (1 + (np.random.rand() - 0.5) * 0.02), 2)
        gap = round(((simulated_realtime_price / yf_price) - 1) * 100, 2)
        
        analysis = "✅ 視覚的確証: トレンド継続中。画像上の価格は予測モデルと一致しています。"
        if abs(gap) > 1.5:
            analysis = "⚠️ 警告: yfinance(20分前)と画像(現在)に大きな乖離があります。慎重に判断してください。"
        
        return jsonify({
            "status": "success",
            "price": simulated_realtime_price,
            "gap": gap,
            "gap_status": "safe" if abs(gap) < 1.0 else "warning",
            "analysis": analysis
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/generate_script', methods=['GET'])
def generate_video_script():
    try:
        db = load_latest_database()
        top_picks = db.sort_values(by='score', ascending=False).head(3)
        
        script = "# Sniper AI Daily Briefing\n\n"
        script += "司令官、今日のスナイプ候補を報告します。なのだ！\n\n"
        
        for _, row in top_picks.iterrows():
            script += f"🚀 注目銘柄: {row['ticker']}\n"
            script += f"期待値は {row['true_ev']}%。{row['stars']}。{row['analysis']}\n\n"
            
        script += "最終判断は画像診断（Visual Recon）を忘れずに。🥇🦾✨"
        
        return jsonify({"status": "success", "script": script})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/post_mortem', methods=['GET'])
def get_post_mortem():
    try:
        if not os.path.exists("trade_log.csv"): return jsonify({"analysis": "データがまだありません。"})
        df = pd.read_csv("trade_log.csv").tail(5) # 直近5件を分析
        
        losses = df[df['pnl_rate'] < 0]
        if losses.empty: return jsonify({"analysis": "最近のトレードは完璧です！この調子を維持しましょう。なのだ！🥇🦾✨"})
        
        worst_trade = losses.sort_values(by='pnl_rate').iloc[0]
        analysis = f"📉 直近の課題: {worst_trade['ticker']} での {worst_trade['pnl_rate']}% の損失が目立ちます。\n"
        
        if worst_trade['exit_reason'] == "Stop Loss":
            analysis += "損切り設定は機能していますが、エントリー時のボラティリティに対するマージンが不足していた可能性があります。"
        elif worst_trade['exit_reason'] == "Time Exit":
            analysis += "時間切れによる撤退です。トレンドの初動を捉えきれなかった可能性があります。"
            
        return jsonify({"analysis": analysis})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
def sell_trade():
    try:
        data = request.json
        ticker = data['ticker']
        # ExecutionEngine側での削除処理
        positions = engine.load_positions()
        positions = [p for p in positions if p['ticker'] != ticker]
        engine.save_positions(positions)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

from sector_analyzer import SectorAnalyzer

@app.route('/api/sectors', methods=['GET'])
def get_sector_flow():
    try:
        analyzer = SectorAnalyzer()
        flow = analyzer.analyze_flow()
        return jsonify(flow)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

from stress_tester import StressTester

@app.route('/api/stress_test', methods=['GET'])
def get_stress_test():
    try:
        tester = StressTester()
        result = tester.run_simulation()
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/strong_entries', methods=['GET'])
def get_strong_entries():
    """Return list of entries marked as STRONG ENTRY with key metrics."""
    db = load_latest_database()
    if db.empty:
        return jsonify([])
    strong = db[db['mechanical_rule'] == '🎯 STRONG ENTRY']
    # 必要な列だけ抽出して JSON 化
    result = strong[['ticker', 'true_ev', 'confidence', 'pattern_score']].copy()
    # 小数点整形
    result['true_ev'] = result['true_ev'].round(4)
    result['confidence'] = result['confidence'].round(2)
    result['pattern_score'] = result['pattern_score'].round(1)
    return jsonify(result.to_dict(orient='records'))

@app.route('/api/recalc', methods=['POST'])
def recalc_ev():
    """V17.0: 非線形タイム・ディケイ & 5段階ボラティリティ判定"""
    try:
        import math
        data = request.json
        ticker = data['ticker']
        live_price = float(data['live_price'])
        
        db = load_latest_database()
        row = db[db['ticker'] == ticker]
        if row.empty:
            return jsonify({"status": "error", "message": "Ticker not found"}), 404
        
        row = row.iloc[0]
        signal_price = float(row['price'])
        signal_ev = float(row['true_ev']) / 100
        volatility = float(row.get('volatility', 0.01))
        
        # --- ⏳ V17.0: Exponential Time Decay ---
        signal_ts = datetime.fromisoformat(row['signal_timestamp'])
        elapsed_mins = (datetime.now() - signal_ts).total_seconds() / 60
        max_horizon = 30
        
        # 指数関数的減衰: 最初は緩やかに、後半急激に優位性が失われる
        decay_ratio = elapsed_mins / max_horizon
        time_decay = max(0.3, math.exp(-decay_ratio))
        
        adjusted_ev = signal_ev * time_decay
        target_price = signal_price * (1 + adjusted_ev)
        
        # 現在価格での実質期待値
        new_ev = (target_price - live_price) / live_price
        
        # --- 🛡️ V17.0: 5-Tier Verdict System ---
        price_gap = (live_price - signal_price) / signal_price
        risk_unit = volatility # 1リスク単位
        
        if price_gap > 0.02:
            verdict = "🚫 TOO LATE"
        elif new_ev > (risk_unit * 3):
            verdict = "⚡ STRONG PREDATOR"
        elif new_ev > (risk_unit * 1.5):
            verdict = "✅ GO"
        elif new_ev > 0:
            verdict = "⚠️ WEAK EDGE"
        else:
            verdict = "⏳ WAIT"
        
        return jsonify({
            "status": "success",
            "ticker": ticker,
            "live_price": live_price,
            "new_ev": round(new_ev * 100, 3),
            "time_decay": round(time_decay, 2),
            "gap": round(price_gap * 100, 2),
            "verdict": verdict
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    print("Sniper AI: Portfolio Backend starting at http://localhost:5000")
    app.run(port=5000, debug=True)
