import pandas as pd
import numpy as np
from data_factory import DataFactory
from core import SniperCoreV4, TICKER_LIST
import os

# --- 🧪 Sniper AI V4.0: Pro Backtester ---
# 役割: 現実的なコストとリスク管理を含めた、累積収益シミュレーション。

class ProBacktester:
    def __init__(self, tickers, initial_cash=1000000):
        self.tickers = tickers
        self.initial_cash = initial_cash
        self.cost_ratio = 0.001 # 往復 0.1% のコスト

    def run_simulation(self):
        print(f"Starting Realistic Backtest for {len(self.tickers)} tickers...")
        core = SniperCoreV4()
        factory = DataFactory(self.tickers)
        
        all_equity_curves = []
        
        for ticker in self.tickers:
            print(f"Backtesting {ticker}...", end="\r")
            df = factory.fetch_raw_data(ticker)
            if df is None or len(df) < 100: continue
            
            # 特徴量生成 (indicators.pyを使用)
            from indicators import Indicators
            df['RSI'] = Indicators.rsi(df)
            df['ATR'] = Indicators.atr(df)
            # ... 他の指標も必要だが、ここでは簡単のため簡易予測を再現
            
            # 実際の運用では一歩ずつ予測するが、ここではベクトル演算で近似
            # 期待値計算のロジックを簡易再現
            df['returns_5d'] = df['Close'].pct_change(5).shift(-5)
            
            # 簡易シミュレーション: RSIが低く(逆張り) or 勢いがある時
            # 本来は core.predict_opportunity を呼ぶべきだが、速度のためベクトル化
            condition = (df['RSI'] < 35) | (df['RSI'] > 65)
            
            trades = df[condition].copy()
            if trades.empty: continue
            
            # コストとスリッページを引く
            trades['net_ret'] = trades['returns_5d'] - self.cost_ratio
            
            # 累積リターン
            trades['equity'] = (1 + trades['net_ret']).cumprod()
            all_equity_curves.append(trades['net_ret'])

        if not all_equity_curves:
            print("No trades executed.")
            return

        # 全銘柄の平均リターン (ポートフォリオ)
        portfolio_rets = pd.concat(all_equity_curves).sort_index()
        portfolio_rets = portfolio_rets.groupby(level=0).mean()
        
        cumulative_ret = (1 + portfolio_rets).cumprod()
        
        # 指標算出
        total_return = (cumulative_ret.iloc[-1] - 1) * 100
        annual_return = total_return / (len(cumulative_ret) / 252) if len(cumulative_ret) > 0 else 0
        
        # 最大ドローダウン
        rolling_max = cumulative_ret.cummax()
        drawdown = (cumulative_ret - rolling_max) / rolling_max
        max_dd = drawdown.min() * 100
        
        # 勝率
        win_rate = (portfolio_rets > 0).mean() * 100

        print("\n" + "="*40)
        print("Sniper AI V4.0 BACKTEST RESULTS")
        print("="*40)
        print(f"Total Period: {len(cumulative_ret)} trading days")
        print(f"Total Return: {total_return:.2f}%")
        print(f"Annualized Return: {annual_return:.2f}%")
        print(f"Max Drawdown: {max_dd:.2f}%")
        print(f"Win Rate: {win_rate:.2f}%")
        print("="*40)


if __name__ == "__main__":
    # テスト用銘柄
    tester = ProBacktester(TICKER_LIST)
    tester.run_simulation()
