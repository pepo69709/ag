import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def get_japanese_stock_data(ticker_symbol, start_date, end_date):
    """
    Japanese stock symbols need to end with .T (e.g., 7203.T for Toyota)
    """
    if not ticker_symbol.endswith(".T"):
        ticker_symbol += ".T"
        
    print(f"Fetching data for {ticker_symbol} from {start_date} to {end_date}...")
    stock = yf.Ticker(ticker_symbol)
    df = stock.history(start=start_date, end=end_date)
    return df

if __name__ == "__main__":
    # Test fetch for Toyota (7203.T)
    data = get_japanese_stock_data("7203.T", "2023-01-01", "2023-12-31")
    print(data.head())
    # Save to CSV for convenience
    data.to_csv("7203_stock_data.csv")
    print("Saved to 7203_stock_data.csv")
