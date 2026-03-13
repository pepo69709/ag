import pandas as pd
import os

def migrate_csv():
    csv_file = "trade_tracker.csv"
    if not os.path.exists(csv_file):
        return
        
    df = pd.read_csv(csv_file)
    if 'label' not in df.columns:
        print("Adding 'label' column to trade_tracker.csv...")
        df['label'] = None
        df.to_csv(csv_file, index=False, encoding='utf-8')
        print("Migration complete.")
    else:
        print("'label' column already exists.")

if __name__ == "__main__":
    migrate_csv()
