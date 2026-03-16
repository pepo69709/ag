import config
import yfinance as yf
import pandas as pd

def expand_tickers():
    current = set(config.WATCH_LIST)
    all_jp_tickers = []
    
    # 日本株の一般的なレンジを走査して追加 (1300-9999)
    # 効率のため、主要な番号を狙い撃ち
    ranges = [
        (1300, 1400), (1700, 1999), (2000, 2999), (3000, 3999), 
        (4000, 4999), (5000, 5999), (6000, 6999), (7000, 7999), 
        (8000, 8999), (9000, 9990)
    ]
    
    new_added = []
    for start, end in ranges:
        if len(new_added) >= 1000: break
        for i in range(start, end + 1):
            t = f"{i}.T"
            if t not in current:
                new_added.append(t)
            if len(new_added) >= 1000: break
            
    extended_list = sorted(list(current) + new_added)
    
    # config.py を書き換える
    with open("config.py", "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    with open("config.py", "w", encoding="utf-8") as f:
        in_list = False
        for line in lines:
            if "WATCH_LIST = [" in line:
                f.write("WATCH_LIST = [\n")
                # 10個ずつ書く
                for i in range(0, len(extended_list), 10):
                    row = ", ".join([f"'{x}'" for x in extended_list[i:i+10]])
                    f.write(f"    {row},\n")
                f.write("]\n")
                in_list = True
            elif in_list:
                if "]" in line:
                    in_list = False
            else:
                f.write(line)

if __name__ == "__main__":
    expand_tickers()
    print("✅ WATCH_LIST has been expanded to 1500 tickers.")
