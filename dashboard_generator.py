import pandas as pd
import yfinance as yf
import os
import json
from datetime import datetime

def generate_dashboard(last_sync_time=None):
    if last_sync_time is None:
        last_sync_time = datetime.now().strftime('%m/%d %H:%M')
    csv_file = "trade_tracker.csv"
    if not os.path.exists(csv_file): return

    try:
        df = pd.read_csv(csv_file)
        df['ticker'] = df['ticker'].str.strip().str.upper()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
    except: return
        
    if df.empty: return

    # 銘柄ごとの最新価格取得
    all_tickers = sorted(df['ticker'].unique().tolist())
    try:
        current_data = yf.download(all_tickers, period="1d", interval="1m", progress=False, auto_adjust=True)
        prices = {}
        for t in all_tickers:
            try:
                if len(all_tickers) > 1:
                    series = current_data['Close'][t].dropna()
                    prices[t] = series.iloc[-1] if not series.empty else 0
                else:
                    prices[t] = current_data['Close'].iloc[-1]
            except: prices[t] = 0
    except:
        prices = {t: 0 for t in all_tickers}

    assets_data = []
    for ticker in all_tickers:
        t_df = df[df['ticker'] == ticker].sort_values('timestamp')
        curr_p = prices.get(ticker, 0)
        
        # グラフ用データ：確信度と、「その時買っていたら今の損益はどうなっていたか」
        history_probs = t_df['win_prob'].tolist()
        history_pnl = []
        for entry_p in t_df['entry_price']:
            val = ((curr_p / entry_p) - 1) * 100 if curr_p > 0 else 0
            history_pnl.append(round(val, 2))
            
        history_times = t_df['timestamp'].dt.strftime('%m/%d %H:%M').tolist()
        
        latest = t_df.iloc[-1]
        total_hits = len(t_df)
        high_prob_now = latest['win_prob'] >= 80
        
        # タイルの色とサイズ判定
        if total_hits == 1:
            color = "rgba(0, 210, 255, 0.4)" # 新規
            size = "small"
        elif high_prob_now:
            color = "rgba(0, 255, 136, 0.6)" # 安定
            size = "large"
        else:
            color = "rgba(255, 46, 99, 0.6)" # 警告
            size = "large"

        assets_data.append({
            "ticker": ticker.split('.')[0],
            "full_ticker": ticker,
            "size": size,
            "color": color,
            "prob": latest['win_prob'],
            "latest_pnl": history_pnl[-1],
            "curr_price": curr_p,
            "history_probs": history_probs,
            "history_pnl": history_pnl,
            "history_times": history_times,
            "last_seen": latest['timestamp'].strftime('%m/%d %H:%M')
        })

    assets_data = sorted(assets_data, key=lambda x: (x['size'] == "large", x['prob']), reverse=True)

    # JSON データを埋め込む
    json_assets = json.dumps(assets_data)

    html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>AI SYNERGY COMMAND v7</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;900&family=Dela+Gothic+One&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #03050a;
            --stable: #00ff88;
            --rising: #00d2ff;
            --danger: #ff2e63;
        }}
        body {{ background: var(--bg); color: white; font-family: 'Outfit', sans-serif; padding: 40px; margin:0; }}
        .matrix {{ display: flex; flex-wrap: wrap; gap: 20px; }}
        .tile {{ border-radius: 25px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: 0.3s; }}
        .tile:hover {{ transform: scale(1.05); filter: brightness(1.2); box-shadow: 0 0 30px rgba(255,255,255,0.1); }}
        .small {{ width: 140px; height: 140px; }}
        .large {{ width: 300px; height: 300px; }}
        .ticker-txt {{ font-family: 'Dela Gothic One', cursive; pointer-events: none; }}
        .small .ticker-txt {{ font-size: 28px; }}
        .large .ticker-txt {{ font-size: 80px; text-shadow: 0 0 20px rgba(255,255,255,0.2); }}

        #overlay {{ position: fixed; inset: 0; background: rgba(0,0,0,0.95); display: none; align-items: center; justify-content: center; z-index: 1000; backdrop-filter: blur(15px); }}
        #modal {{ background: #0f172a; width: 95%; max-width: 1000px; padding: 50px; border-radius: 50px; border: 1px solid rgba(255,255,255,0.1); position: relative; }}
        .close {{ position: absolute; top: 30px; right: 40px; cursor: pointer; font-size: 40px; opacity: 0.5; }}
    </style>
</head>
<body>
    <header style="margin-bottom: 40px; display: flex; justify-content: space-between; align-items: flex-end;">
        <div>
            <h1 style="font-weight: 900; color: var(--stable); margin:0; font-size: 48px;">AI SYNERGY COMMAND v7</h1>
            <p style="opacity: 0.5; font-size: 16px; margin: 5px 0 0 0;">金の折れ線グラフ：その判定時にエントリーした場合の現在の通算損益(%)</p>
        </div>
        <div style="text-align: right; border-left: 1px solid rgba(255,255,255,0.1); padding-left: 20px;">
            <div style="font-size: 12px; opacity: 0.4; letter-spacing: 1px;">SYSTEM STATUS</div>
            <div style="color: var(--stable); font-size: 20px; font-weight: 900;">ACTIVE / LIVE</div>
            <div style="font-size: 14px; opacity: 0.6;">LAST CHECK: {last_sync_time}</div>
        </div>
    </header>
    <div class="matrix"></div>
    <div id="overlay" onclick="closeM()">
        <div id="modal" onclick="event.stopPropagation()">
            <span class="close" onclick="closeM()">&times;</span>
            <div id="content"></div>
        </div>
    </div>

    <script>
        const assets = {json_assets};
        function draw() {{
            const grid = document.querySelector('.matrix');
            assets.forEach(a => {{
                const d = document.createElement('div');
                d.className = `tile ${{a.size}}`;
                d.style.backgroundColor = a.color;
                d.innerHTML = `<span class="ticker-txt">${{a.ticker}}</span>`;
                d.onclick = () => openM(a);
                grid.appendChild(d);
            }});
        }}

        let chart;
        function openM(a) {{
            const pColor = a.latest_pnl >= 0 ? 'var(--stable)' : 'var(--danger)';
            document.getElementById('overlay').style.display = 'flex';
            document.getElementById('content').innerHTML = `
                <div style="font-size: 14px; opacity: 0.5; letter-spacing: 2px;">RELATIONAL ANALYSIS: ${{a.full_ticker}}</div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                    <h2 style="font-size: 110px; font-family: 'Dela Gothic One'; margin: 0;">${{a.ticker}}</h2>
                    <div style="text-align: right;">
                        <div style="color: ${{pColor}}; font-size: 70px; font-weight: 900; line-height: 1;">${{a.latest_pnl >= 0 ? '+' : ''}}${{a.latest_pnl}}%</div>
                        <div style="font-size: 16px; opacity: 0.6; margin-top: 10px;">LATEST ENTRY P/L</div>
                    </div>
                </div>
                <div style="margin-top: 30px; background: rgba(0,0,0,0.3); border-radius: 40px; padding: 30px;">
                    <canvas id="chart"></canvas>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 25px; font-size: 13px; font-weight: 700;">
                    <span style="color: #00d2ff;">● AI CONFIDENCE (%)</span>
                    <span style="color: #ffd700;">● POTENTIAL P/L (%) IF BOUGHT AT TIME</span>
                    <span style="opacity: 0.4;">LAST SYNC: ${{a.last_seen}}</span>
                </div>
            `;

            const ctx = document.getElementById('chart').getContext('2d');
            if (chart) chart.destroy();
            chart = new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: a.history_times,
                    datasets: [
                        {{
                            label: 'AI 確信度 (%)',
                            data: a.history_probs,
                            borderColor: '#00d2ff',
                            borderWidth: 5, yAxisID: 'y_prob', tension: 0.4, pointRadius: 6, fill: true,
                            backgroundColor: 'rgba(0, 210, 255, 0.05)'
                        }},
                        {{
                            label: '損益推移 (%)',
                            data: a.history_pnl,
                            borderColor: '#ffd700',
                            borderDash: [5, 5],
                            borderWidth: 3, yAxisID: 'y_pnl', tension: 0.2, pointRadius: 10, pointStyle: 'rectRot'
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y_prob: {{ position: 'left', min: 0, max: 105, grid: {{ color: 'rgba(255,255,255,0.05)' }}, title: {{ display: true, text: '確信度 (%)' }} }},
                        y_pnl: {{ position: 'right', grid: {{ drawOnChartArea: false }}, title: {{ display: true, text: '現在損益 (%)' }} }}
                    }},
                    plugins: {{ legend: {{ display: false }} }}
                }}
            }});
        }}
        function closeM() {{ document.getElementById('overlay').style.display = 'none'; }}
        draw();
        setTimeout(() => location.reload(), 60000);
    </script>
</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    generate_dashboard()
