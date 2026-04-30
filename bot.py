import numpy as np
import pandas as pd
from datetime import datetime, time

# --- Sniper AI V1.3: The Battle-Hardened Vanguard ---
# 役割: 実戦検証用プロトタイプ。連敗制御と詳細ログ機能を搭載。

class EternalHunter:
    def __init__(self, initial_capital=1000000):
        self.pb_threshold = 0.8
        self.score_threshold = 0.72
        
        # 防衛設定
        self.min_daily_volume_jpy = 1000000000 
        self.max_spread_ratio = 0.001
        self.capital_per_trade_ratio = 0.05 
        self.max_positions = 5
        
        # 資金管理・ブレーキ
        self.initial_capital = initial_capital
        self.current_equity = initial_capital
        self.daily_losses = 0
        self.max_dd_ratio = 0.05
        self.is_paused = False
        
        # ログ (後でCSV出力可能にする)
        self.trade_logs = []

    def is_safe_to_trade(self, ts):
        """
        時間帯 + 自律ブレーキの確認。
        """
        if self.is_paused: return False
        
        # 1. 時間帯
        curr_time = ts.time()
        morning = time(9, 15) <= curr_time <= time(11, 25)
        afternoon = time(12, 35) <= curr_time <= time(14, 45)
        if not (morning or afternoon): return False
        
        # 2. 当日連敗制限 (3連敗で停止)
        if self.daily_losses >= 3: return False
        
        # 3. DD制限 (5%ドロップで停止)
        if (self.current_equity / self.initial_capital) < (1 - self.max_dd_ratio):
            self.is_paused = True
            return False
            
        return True

    def calculate_score(self, ticker, df_slice, bid_ask=None):
        if not self.is_safe_to_trade(df_slice.index[-1]): return 0, 0
        
        try:
            # スプレッド制限
            if bid_ask:
                bid, ask = bid_ask
                if (ask - bid) / ((ask + bid) / 2) > self.max_spread_ratio: return 0, 0

            # 物理判定
            close = df_slice['Close'].iloc[-1]
            high_10 = df_slice['High'].rolling(10).max().iloc[-1]
            vol = df_slice['Close'].pct_change().rolling(20).std().iloc[-1]
            pb_ratio = ((high_10 - close) / (high_10 + 1e-9)) / (vol + 1e-9)
            
            if pb_ratio < self.pb_threshold or vol < 0.003: return 0, pb_ratio
            
            pb_score = np.exp(-((pb_ratio - 2.5) ** 2) / (2 * 1.5 ** 2))
            if pb_score > self.score_threshold and df_slice['Close'].pct_change(1).iloc[-1] > 0:
                return pb_score, pb_ratio
            return 0, 0
        except: return 0, 0

    def record_trade(self, ticker, entry_p, exit_p, theory_entry_p, spread, reason):
        """
        分析用の詳細ログを記録。
        """
        pnl = (exit_p / entry_p) - 1
        slippage = (entry_p / theory_entry_p) - 1
        
        log = {
            "ts": datetime.now(),
            "ticker": ticker,
            "pnl": pnl,
            "slip": slippage,
            "spread": spread,
            "reason": reason
        }
        self.trade_logs.append(log)
        
        # ブレーキ更新
        if pnl < 0: self.daily_losses += 1
        else: self.daily_losses = 0
        self.current_equity *= (1 + pnl)

    def get_exit_decision(self, pos, curr_price, ts):
        pnl = (curr_price / pos["entry_price"]) - 1
        trail_k = 1.0 * np.clip(pos["pb_ratio"] / 3.0, 0.5, 1.5) * np.clip(pnl / 0.02, 0.8, 2.0)
        
        if curr_price <= pos["entry_price"] - (pos["entry_atr"] * 2.0): return True, "STOP LOSS"
        if curr_price <= pos["highest_price"] - (pos["entry_atr"] * trail_k) and pos["highest_price"] > pos["entry_price"]: return True, "TRAILING"
        if (ts - pos["entry_ts"]).total_seconds() / 60 >= 180: return True, "TIME EXIT"
        return False, None
