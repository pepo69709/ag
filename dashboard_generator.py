import pandas as pd
import yfinance as yf
import os
from datetime import datetime

def generate_dashboard():
    csv_file = "trade_tracker.csv"
    if not os.path.exists(csv_file):
        print("CSV file not found.")
        return

    df = pd.read_csv(csv_file)
    if df.empty:
        print("CSV is empty.")
        return

    # 重複を除去（直近の信号を優先）して最新の現在価格を取得
    unique_tickers = df['ticker'].unique().tolist()
    try:
        current_data = yf.download(unique_tickers, period="1d", interval="1m", progress=False, auto_adjust=True)
        prices = {}
        for ticker in unique_tickers:
            if len(unique_tickers) > 1:
                prices[ticker] = current_data['Close'][ticker].iloc[-1]
            else:
                prices[ticker] = current_data['Close'].iloc[-1]
    except:
        prices = {t: 0 for t in unique_tickers}

    # 日時でソート（新しい順）
    df = df.sort_values(by="timestamp", ascending=False).head(20) # 直近20件

    # HTML 生成
    html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI AI PATROL COMMAND CENTER</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0b0e14;
            --card-bg: rgba(23, 28, 38, 0.9);
            --accent-gold: #ffcf4d;
            --accent-blue: #00d2ff;
            --text-main: #e0e6ed;
            --text-dim: #94a3b8;
            --success: #10b981;
            --danger: #ef4444;
        }}

        body {{
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(circle at 50% 0%, rgba(0, 210, 255, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 100% 100%, rgba(255, 207, 77, 0.05) 0%, transparent 50%);
            color: var(--text-main);
            font-family: 'Outfit', sans-serif;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }}

        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{
            display: flex; justify-content: space-between; align-items: center;
            padding: 20px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 30px;
        }}
        .logo {{ font-size: 24px; font-weight: 700; background: linear-gradient(90deg, var(--accent-blue), var(--accent-gold)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; }}
        
        .card {{
            background: var(--card-bg); backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 24px; padding: 24px;
            position: relative; transition: all 0.3s ease;
        }}
        .card:hover {{ transform: translateY(-5px); border-color: var(--accent-gold); }}
        
        .ticker-name {{ font-size: 32px; font-weight: 700; font-family: 'JetBrains Mono', monospace; margin-bottom: 5px; }}
        .timestamp {{ font-size: 12px; color: var(--text-dim); margin-bottom: 20px; }}
        
        .status-box {{
            background: rgba(255, 255, 255, 0.03); border-radius: 16px; padding: 15px; margin-bottom: 20px;
        }}
        .status-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
        .label {{ font-size: 12px; color: var(--text-dim); text-transform: uppercase; }}
        .price-val {{ font-size: 18px; font-weight: 700; }}
        
        .profit-badge {{
            padding: 4px 12px; border-radius: 8px; font-weight: 700; font-size: 20px;
        }}
        .profit-up {{ background: rgba(16, 185, 129, 0.15); color: var(--success); }}
        .profit-down {{ background: rgba(239, 68, 68, 0.15); color: var(--danger); }}
        
        .progress-container {{ width: 100%; height: 8px; background: rgba(255, 255, 255, 0.05); border-radius: 4px; overflow: hidden; margin-top: 10px; }}
        .progress-bar {{ height: 100%; transition: width 0.5s ease; }}
        
        .confidence-chip {{
            display: inline-block; padding: 2px 10px; border-radius: 6px; font-size: 12px; font-weight: 700; margin-bottom: 15px;
            background: linear-gradient(90deg, var(--accent-blue), var(--accent-gold)); color: #000;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">AI STRATEGY COMMAND CENTER</div>
            <div style="text-align: right">
                <div style="font-size: 12px; color: var(--text-dim)">LAST UPDATE</div>
                <div style="font-size: 18px; font-weight: 700">{datetime.now().strftime('%H:%M:%S')}</div>
            </div>
        </header>

        <div class="grid">
"""

    for _, row in df.iterrows():
        ticker = row['ticker']
        entry_p = row['entry_price']
        curr_p = prices.get(ticker, 0)
        
        if curr_p > 0:
            profit_pct = (curr_p / entry_p - 1) * 100
            # 3%をゴールとした進捗率
            progress = min(100, max(0, (profit_pct / 3.0) * 100))
        else:
            profit_pct = 0
            progress = 0
            
        profit_class = "profit-up" if profit_pct >= 0 else "profit-down"
        bar_color = "var(--success)" if profit_pct >= 0 else "var(--danger)"
        
        html_content += f"""
            <div class="card">
                <div class="confidence-chip">AI CONFIDENCE: {row['win_prob']:.1f}%</div>
                <div class="ticker-name">{ticker}</div>
                <div class="timestamp">推奨時刻: {row['timestamp']}</div>

                <div class="status-box">
                    <div class="status-row">
                        <span class="label">推奨時価格</span>
                        <span class="price-val">{entry_p:,.0f} 円</span>
                    </div>
                    <div class="status-row" style="border-top: 1px solid rgba(255,255,255,0.05); padding-top: 10px; margin-top: 10px;">
                        <span class="label">現在損益 (％)</span>
                        <span class="profit-badge {profit_class}">{profit_pct:+.2f}%</span>
                    </div>
                    <div class="label" style="margin-top: 15px;">3% 利確ターゲットへの進捗</div>
                    <div class="progress-container">
                        <div class="progress-bar" style="width: {progress}%; background: {bar_color};"></div>
                    </div>
                </div>
            </div>
"""

    html_content += """
        </div>
        <footer style="margin-top: 50px; text-align: center; color: var(--text-dim); font-size: 12px;">
            ※ 現在価格は yfinance 経由で取得しています。実際の約定価格とは異なる場合があります。<br>
            &copy; 2026 AI Trading System Engine
        </footer>
    </div>
</body>
</html>
"""

    with open("dashboard.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("✨ Dashboard updated with Live Performance tracking.")

if __name__ == "__main__":
    generate_dashboard()
