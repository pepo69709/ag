import pandas as pd
import numpy as np

class Backtester:
    def __init__(self, data, initial_capital=10000):
        self.data = data.copy()
        self.initial_capital = initial_capital
        self.trades = [] # Track each trade details

    def run(self, strategy_func):
        signals = strategy_func(self.data)
        self.data['Signal'] = signals
        
        capital = self.initial_capital
        positions = 0
        portfolio_values = []
        
        entry_price = 0
        entry_date = None
        entry_news = ""

        for i in range(len(self.data)):
            price = self.data['Close'].iloc[i]
            signal = self.data['Signal'].iloc[i]
            date = self.data.index[i]
            news = self.data['News_Event'].iloc[i] if 'News_Event' in self.data.columns else ""
            
            # --- BUY Logic ---
            if signal == 1:
                if capital >= price:
                    buy_count = capital // price
                    positions += buy_count
                    capital -= buy_count * price
                    
                    entry_price = price
                    entry_date = date
                    entry_news = news
                
            # --- SELL Logic ---
            elif signal == -1:
                if positions > 0:
                    exit_price = price
                    profit = (exit_price - entry_price) * positions
                    return_pct = (exit_price / entry_price - 1) * 100
                    
                    self.trades.append({
                        'Entry_Date': entry_date,
                        'Exit_Date': date,
                        'News': entry_news,
                        'Entry_Price': entry_price,
                        'Exit_Price': exit_price,
                        'Return_Pct': return_pct,
                        'Profit': profit
                    })
                    
                    capital += positions * price
                    positions = 0
                
            total_value = capital + (positions * price)
            portfolio_values.append(total_value)
            
        self.data['Portfolio_Value'] = portfolio_values
        self.final_return = (portfolio_values[-1] / self.initial_capital - 1) * 100
        
        return self.data, self.trades
