import yfinance as yf
import pandas as pd
import os
import requests
from datetime import datetime
import config

DB_FILE = "database.csv"
GAS_URL = os.environ.get("GAS_WEBHOOK_URL") or config.GAS_WEBHOOK_URL

def update_db(ticker, profit, status, name="TARGET", entry="---"):
    df = pd.read_csv(DB_FILE)
    if ticker in df["ticker"].values:
        df.loc[df["ticker"] == ticker, ["profit", "status", "name", "entry_p"]] = [profit, status, name, entry]
    else:
        new_row = pd.DataFrame([{"ticker": ticker, "name": name, "profit": profit, "status": status, "entry_p": entry}])
        df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(DB_FILE, index=False)

def run_patrol():
    print("🚀 Sniper AI: Starting Patrol...")
    for ticker in config.WATCH_LIST:
        try:
            data = yf.Ticker(ticker).history(period="1d")
            if data.empty: continue
            
            curr = data["Close"].iloc[-1]
            open_p = data["Open"].iloc[0]
            profit = round((curr / open_p - 1) * 100, 2)
            
            # Simple Logic
            status = 0
            if profit >= config.EXIT_PROFIT_TARGET: status = 1
            elif profit <= -config.EXIT_STOP_LOSS: status = 2
            
            update_db(ticker, profit, status, entry=open_p)
            print(f"✅ {ticker}: {profit}% (Status: {status})")
        except Exception as e:
            print(f"❌ Error {ticker}: {e}")

if __name__ == "__main__":
    run_patrol()
