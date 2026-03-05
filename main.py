import pandas as pd
import numpy as np
import os
import json
from engine import Backtester
from data_loader import get_japanese_stock_data
import config

def generate_web_dashboard(master_df, kw_rank):
    """
    バックテスト結果をプレミアムなウェブダッシュボード形式（HTML/JS）で生成する
    """
    # グラフ用データ準備
    master_df = master_df.sort_values('Entry_Date')
    cumulative_profit = [0] + list(master_df['Profit'].cumsum().astype(float))
    trade_labels = ["スタート"] + [f"{row['Ticker']} - {row['Hit_Keyword']}" for _, row in master_df.iterrows()]
    
    # キーワードランキングをJSON形式に
    kw_data = kw_rank.reset_index().to_dict(orient='records')
    
    # 統計情報の計算
    total_trades = len(master_df)
    win_rate = (master_df['Return_Pct'] > 0).mean() * 100
    pos_p = master_df[master_df['Profit'] > 0]['Profit'].sum()
    neg_p = abs(master_df[master_df['Profit'] < 0]['Profit'].sum())
    pf = pos_p / neg_p if neg_p > 0 else (pos_p if pos_p > 0 else 0)

    html_template = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Stock Backtest Elite Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Outfit:wght@500;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg: #0f172a;
                --card-bg: #1e293b;
                --primary: #fbbf24;
                --text: #f8fafc;
                --text-dim: #94a3b8;
                --success: #10b981;
                --danger: #ef4444;
            }}
            body {{
                font-family: 'Inter', sans-serif;
                background-color: var(--bg);
                color: var(--text);
                margin: 0;
                padding: 40px 20px;
                line-height: 1.6;
            }}
            .container {{
                max-width: 1100px;
                margin: 0 auto;
            }}
            header {{
                text-align: center;
                margin-bottom: 50px;
            }}
            h1 {{
                font-family: 'Outfit', sans-serif;
                font-size: 3rem;
                margin-bottom: 10px;
                background: linear-gradient(90deg, #fbbf24, #f59e0b);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }}
            .stat-card {{
                background: var(--card-bg);
                padding: 25px;
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.05);
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                transition: transform 0.3s ease;
            }}
            .stat-card:hover {{ transform: translateY(-5px); }}
            .stat-label {{ color: var(--text-dim); font-size: 0.9rem; font-weight: 600; text-transform: uppercase; }}
            .stat-value {{ font-size: 2rem; font-weight: 800; font-family: 'Outfit'; margin-top: 5px; }}
            .chart-container {{
                background: var(--card-bg);
                padding: 30px;
                border-radius: 24px;
                margin-bottom: 40px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            .keyword-table {{
                width: 100%;
                border-collapse: collapse;
                background: var(--card-bg);
                border-radius: 20px;
                overflow: hidden;
            }}
            .keyword-table th, .keyword-table td {{
                padding: 15px 20px;
                text-align: left;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }}
            .keyword-table th {{ background: rgba(255,255,255,0.05); color: var(--text-dim); }}
            .trend-up {{ color: var(--success); }}
            .trend-down {{ color: var(--danger); }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Elite Backtest Report</h1>
                <p style="color: var(--text-dim)">日本のトップ銘柄に対する過去10年間のエリート厳選戦略の成果</p>
            </header>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">利益因子 (PF)</div>
                    <div class="stat-value" style="color: var(--primary)">{pf:.2f}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">勝率</div>
                    <div class="stat-value">{win_rate:.1f}%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">精鋭トレード数</div>
                    <div class="stat-value">{total_trades}回</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">累計利益</div>
                    <div class="stat-value" style="color: var(--success)">+{cumulative_profit[-1]:,.0f}円</div>
                </div>
            </div>

            <div class="chart-container">
                <h2 style="margin-top: 0; font-family: 'Outfit'">資産成長カーブ</h2>
                <canvas id="profitChart" height="120"></canvas>
            </div>

            <div class="chart-container">
                <h2 style="margin-top: 0; font-family: 'Outfit'">キーワード別勝率ランキング</h2>
                <table class="keyword-table">
                    <thead>
                        <tr>
                            <th>キーワード</th>
                            <th>回数</th>
                            <th>平均利益率</th>
                            <th>勝率</th>
                            <th>累計損益</th>
                        </tr>
                    </thead>
                    <tbody id="keyword-list">
                    </tbody>
                </table>
            </div>
        </div>

        <script>
            // 資産グラフ
            const ctx = document.getElementById('profitChart').getContext('2d');
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: {json.dumps(trade_labels, ensure_ascii=False)},
                    datasets: [{{
                        label: '累積損益 (円)',
                        data: {json.dumps(cumulative_profit)},
                        borderColor: '#fbbf24',
                        backgroundColor: 'rgba(251, 191, 36, 0.1)',
                        borderWidth: 4,
                        fill: true,
                        tension: 0.1,
                        pointRadius: 6,
                        pointBackgroundColor: '#fbbf24'
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{
                        y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#94a3b8' }} }},
                        x: {{ grid: {{ display: false }}, ticks: {{ display: false }} }}
                    }}
                }}
            }});

            // キーワード表
            const kwData = {json.dumps(kw_data, ensure_ascii=False)};
            const tableBody = document.getElementById('keyword-list');
            kwData.forEach(row => {{
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="font-weight: 700;">${{row.Hit_Keyword}}</td>
                    <td>${{row['トレード回数']}}</td>
                    <td class="${{row['平均利益率(%)'] >= 0 ? 'trend-up' : 'trend-down'}}">${{row['平均利益率(%)'].toFixed(2)}}%</td>
                    <td>${{row['勝率(%)'].toFixed(1)}}%</td>
                    <td class="${{row['累計利益(円)'] >= 0 ? 'trend-up' : 'trend-down'}}">${{row['累計利益(円)'].toLocaleString()}}円</td>
                `;
                tableBody.appendChild(tr);
            }});
        </script>
    </body>
    </html>
    """
    
    with open("dashboard.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"\n>> プレミアムダッシュボードを 'dashboard.html' に生成しました。ブラウザでご覧ください。")

def run_elite_backtest_to_web():
    # 20銘柄
    tickers = config.WATCH_LIST[:20]
    initial_money = 10000
    
    all_trades = []
    
    print("\n" + "="*80)
    print("      【プレミアム・分析レポート】バックテスト実行中...")
    print("="*80)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    news_df = pd.read_csv(os.path.join(script_dir, "mock_news.csv"), parse_dates=['Date'])
    news_df['Date'] = pd.to_datetime(news_df['Date']).dt.normalize()
    news_df.set_index('Date', inplace=True)

    for ticker in tickers:
        print(f">> Analyzing {ticker}...", end="\r")
        df = get_japanese_stock_data(ticker, "2015-01-01", "2024-12-31")
        if df is None or df.empty: continue
        
        df.index = pd.to_datetime(df.index).normalize()
        if df.index.tz is not None: df.index = df.index.tz_localize(None)

        df['SMA25'] = df['Close'].rolling(window=config.SMA_PERIOD).mean()
        df['Avg_Vol'] = df['Volume'].rolling(window=20).mean()
        df['Is_Green'] = df['Close'] > df['Open']
        ticker_df = df.join(news_df[['News_Event']], how='left').fillna("")

        def strategy(data):
            signals = [0] * len(data)
            is_holding, entry_p, days = False, 0, 0
            closes = pd.to_numeric(data['Close'], errors='coerce').values
            opens = pd.to_numeric(data['Open'], errors='coerce').values
            smas = pd.to_numeric(data['SMA25'], errors='coerce').values
            vols = pd.to_numeric(data['Volume'], errors='coerce').values
            avg_vols = pd.to_numeric(data['Avg_Vol'], errors='coerce').values
            is_greens = data['Is_Green'].values
            news_col = data['News_Event'].values

            for i in range(len(data) - 1):
                if is_holding:
                    days += 1
                    ret = (closes[i] / entry_p - 1) * 100
                    if ret <= -1.5 or ret >= 5.0 or days >= 5:
                        signals[i], is_holding = -1, False
                    continue
                
                news = str(news_col[i])
                if not news: continue
                
                # キーワードと環境のチェック (configから読み込み)
                if any(kw in news for kw in config.TARGET_KEYWORDS) and \
                   (not np.isnan(smas[i]) and closes[i] > smas[i]) and \
                   (not np.isnan(avg_vols[i]) and vols[i] > avg_vols[i] * config.VOL_FACTOR) and \
                   is_greens[i]:
                    
                    signals[i+1] = 1 
                    is_holding = True
                    entry_p = opens[i+1] # 翌朝約定
                    days = 0
            return signals

        bt = Backtester(ticker_df, initial_capital=initial_money)
        _, trades = bt.run(strategy)
        for t in trades:
            hits = [kw for kw in config.TARGET_KEYWORDS if kw in t['News']]
            t['Hit_Keyword'] = hits[0] if hits else "その他"
            t['Ticker'] = ticker
            all_trades.append(t)

    master_df = pd.DataFrame(all_trades)
    if not master_df.empty:
        # ランキング集計
        kw_rank = master_df.groupby('Hit_Keyword').agg({
            'Return_Pct': ['count', 'mean', lambda x: (x > 0).mean() * 100],
            'Profit': 'sum'
        })
        kw_rank.columns = ['トレード回数', '平均利益率(%)', '勝率(%)', '累計利益(円)']
        kw_rank = kw_rank.sort_values('勝率(%)', ascending=False)
        
        # Webダッシュボード生成
        generate_web_dashboard(master_df, kw_rank)
    else:
        print("\n条件に一致する結果がありませんでした。")

if __name__ == "__main__":
    run_elite_backtest_to_web()
