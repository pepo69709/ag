import json
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- 🏦 Sniper AI V19.5: Adaptive Predator Exit ---
# 役割: 期待値崩壊(EV Collapse)検知、スコア連動型アダプティブ・トレイルの実装。
# 「エントリー時の確信度」と「現在の期待値」に同期する究極のエグジット・エンジン。

class ExecutionEngine:
    def __init__(self, positions_file="positions.json", log_file="trade_log.csv"):
        self.positions_file = positions_file
        self.log_file = log_file
        
        # 戦略パラメータ (tuned_config があれば上書き)
        self.sl_k = 2.0       # 初期損切: ATR * 2.0 (強固な盾)
        self.tp_k = 3.0       # 利確目標: ATR * 3.0
        self.max_mins = 180   # 最大保持時間: 180分

        if os.path.exists("tuned_config.json"):
            try:
                with open("tuned_config.json", "r") as f:
                    config = json.load(f)
                    self.sl_k = config.get("sl_atr", 2.0)
                    self.tp_k = config.get("tp_atr", 3.0)
                    self.max_mins = config.get("max_mins", 180)
                    print(f"⚙️ Tactical Tuned [V19.5]: SL={self.sl_k}, TP={self.tp_k}, MaxMins={self.max_mins}")
            except Exception: pass

    def load_positions(self):
        if os.path.exists(self.positions_file):
            with open(self.positions_file, "r") as f:
                return json.load(f)
        return []

    def save_positions(self, positions):
        with open(self.positions_file, "w") as f:
            json.dump(positions, f, indent=4)

    def log_trade(self, trade_data):
        df = pd.DataFrame([trade_data])
        if not os.path.exists(self.log_file):
            df.to_csv(self.log_file, index=False, encoding='utf-8-sig')
        else:
            df.to_csv(self.log_file, mode='a', header=False, index=False, encoding='utf-8-sig')

    def check_exits(self, current_prices, current_stats):
        """
        V19.5: Adaptive Predator Logic
        current_prices: {ticker: price}
        current_stats: {ticker: {"ev": float, "score": float}}
        """
        positions = self.load_positions()
        active_positions = []
        closed_trades = []
        now = datetime.now()

        for pos in positions:
            ticker = pos["ticker"]
            if ticker not in current_prices:
                active_positions.append(pos)
                continue

            curr_price = current_prices[ticker]
            entry_price = pos["entry_price"]
            atr = pos.get("entry_atr", curr_price * 0.01)
            
            # 統計データの取得 (V19.5)
            stats = current_stats.get(ticker, {})
            current_ev = stats.get("ev", 0.01) # 不明な場合は維持
            entry_score = pos.get("final_score", 0.5)

            # --- V19.6: Fluid Adaptive Trail (流体適応型トレイル) ---
            # 1. 入力品質による調整 (深い押し目ほど広く)
            pb_ratio = pos.get("pb_ratio", 1.0)
            pb_factor = np.clip(pb_ratio / 3.0, 0.5, 1.5)
            
            # 2. 含み益による調整 (乗れば乗るほど広く、大当たりを狙う)
            profit = (curr_price - entry_price) / (entry_price + 1e-9)
            profit_factor = np.clip(profit / 0.02, 0.8, 2.0)
            
            trail_k = 1.0 * pb_factor * profit_factor
            
            if "highest_price" not in pos or curr_price > pos["highest_price"]:
                pos["highest_price"] = curr_price
            
            highest_price = pos["highest_price"]
            trailing_stop_price = highest_price - (atr * trail_k)

            # 経過時間の算出
            if "entry_timestamp" in pos:
                entry_ts = datetime.fromisoformat(pos["entry_timestamp"])
            else:
                entry_ts = datetime.strptime(pos["entry_date"], "%Y-%m-%d")
            mins_held = (now - entry_ts).total_seconds() / 60
            
            pnl_rate = (curr_price / entry_price) - 1
            stop_loss_price = entry_price - (atr * self.sl_k)
            take_profit_price = entry_price + (atr * self.tp_k)
            
            # --- V19.5: Adaptive Exit Decision ---
            reason = None
            if curr_price <= stop_loss_price:
                reason = "STOP LOSS"
            elif current_ev < 0:
                # 【核心】期待値の崩壊を検知して即座に逃げる
                reason = "EV COLLAPSE"
            elif curr_price <= trailing_stop_price and highest_price > entry_price:
                # 利益が乗った後の適応型トレイル
                reason = "ADAPTIVE TRAILING"
            elif curr_price >= take_profit_price:
                reason = "TAKE PROFIT"
            elif mins_held >= self.max_mins:
                reason = "TIME EXIT"

            if reason:
                trade_result = {
                    "ticker": ticker,
                    "is_shadow": pos.get("is_shadow", False),
                    "entry_ts": entry_ts.isoformat(),
                    "exit_ts": now.isoformat(),
                    "entry_price": entry_price,
                    "exit_price": curr_price,
                    "pnl_rate": round(pnl_rate * 100, 2),
                    "exit_reason": reason,
                    "mins_held": round(mins_held, 1),
                    "entry_score": entry_score
                }
                closed_trades.append(trade_result)
                self.log_trade(trade_result)
                print(f"📡 PREDATOR EXIT [{ticker}]: {reason} | PnL: {trade_result['pnl_rate']}% | Score: {entry_score}")
            else:
                active_positions.append(pos)

        self.save_positions(active_positions)
        return closed_trades
