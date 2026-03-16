import pandas as pd
import yfinance as yf
import os
import json
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

def generate_dashboard(last_sync_time=None):
    if last_sync_time is None:
        last_sync_time = datetime.now(JST).strftime('%m/%d %H:%M')
    csv_file = "trade_tracker.csv"
    if not os.path.exists(csv_file): return

    try:
        df = pd.read_csv(csv_file)
        if df.empty: return
    except: return

    today_str = datetime.now(JST).strftime('%Y-%m-%d')

    # 新フォーマット（date列がある）か旧フォーマットか判定
    if 'date' in df.columns:
        today_df = df[df['date'] == today_str].copy()
        use_new_format = True
    else:
        # 旧フォーマット互換
        today_df = df.copy()
        use_new_format = False

    # 過去の成績サマリー計算
    if use_new_format and 'status' in df.columns:
        total     = len(df[df['status'].notna()])
        achieved  = len(df[df['status'] == '✅ 達成！'])
        missed    = len(df[df['status'] == '❌ 未達'])
        waiting   = len(df[df['status'] == '🕐 待機中'])
        win_rate  = round(achieved / (achieved + missed) * 100, 1) if (achieved + missed) > 0 else 0
        avg_gain  = round(df[df['gain_pct'].notna()]['gain_pct'].mean(), 2) if 'gain_pct' in df.columns else 0
    else:
        total = len(df); achieved = missed = waiting = win_rate = avg_gain = 0

    # 本日のカード用データ
    cards = []
    if use_new_format and not today_df.empty:
        for _, row in today_df.iterrows():
            status   = row.get('status', '🕐 待機中')
            gain     = row.get('gain_pct', None)
            gain_str = f"+{gain:.2f}%" if (gain and not pd.isna(gain)) else "—"
            achieved_time = row.get('achieved_time', None) or "—"

            if status == '✅ 達成！':
                color = "rgba(0,255,136,0.75)"
                grad  = "linear-gradient(135deg, #00ff88 0%, #00b85a 100%)"
                badge = "🎯 GOAL HIT"
            elif status == '❌ 未達':
                color = "rgba(255,46,99,0.75)"
                grad  = "linear-gradient(135deg, #ff2e63 0%, #c81440 100%)"
                badge = "❌ MISSED"
            else:
                color = "rgba(0,180,255,0.5)"
                grad  = "linear-gradient(135deg, rgba(0,180,255,0.7) 0%, rgba(0,80,180,0.8) 100%)"
                badge = "🕐 WAITING"

            cards.append({
                "ticker": str(row['ticker']).replace('.T', ''),
                "full_ticker": str(row['ticker']),
                "entry_price": float(row['entry_price']),
                "entry_time": str(row.get('entry_time', '—')),
                "win_prob": float(row['win_prob']),
                "status": status,
                "badge": badge,
                "gain_str": gain_str,
                "achieved_time": str(achieved_time),
                "color": color,
                "grad": grad,
            })
    else:
        # 旧フォーマットの場合は旧ロジックで代替
        pass

    json_cards = json.dumps(cards, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="120">
    <title>AI 当日+1%狙い ダッシュボード</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;900&family=Dela+Gothic+One&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #03050a;
            --green: #00ff88;
            --blue: #00d2ff;
            --red: #ff2e63;
            --gold: #ffd700;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg);
            color: white;
            font-family: 'Outfit', sans-serif;
            min-height: 100vh;
            padding: 32px;
        }}

        /* ===== ヘッダー ===== */
        header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 32px;
            padding-bottom: 24px;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }}
        .title {{ font-family: 'Dela Gothic One', cursive; font-size: 36px; color: var(--green); }}
        .subtitle {{ font-size: 13px; opacity: 0.45; margin-top: 6px; }}

        /* ===== KPI バー ===== */
        .kpi-bar {{
            display: flex;
            gap: 16px;
            margin-bottom: 36px;
            flex-wrap: wrap;
        }}
        .kpi {{
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 18px 28px;
            flex: 1;
            min-width: 140px;
        }}
        .kpi-label {{ font-size: 11px; opacity: 0.4; letter-spacing: 1.5px; text-transform: uppercase; }}
        .kpi-value {{ font-size: 40px; font-weight: 900; margin-top: 4px; }}
        .kpi-value.green {{ color: var(--green); }}
        .kpi-value.red   {{ color: var(--red); }}
        .kpi-value.gold  {{ color: var(--gold); }}
        .kpi-value.blue  {{ color: var(--blue); }}

        /* ===== カードグリッド ===== */
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 20px;
        }}
        .card {{
            border-radius: 24px;
            padding: 24px;
            border: 1px solid rgba(255,255,255,0.12);
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
            transition: transform 0.3s, box-shadow 0.3s;
            position: relative;
            overflow: hidden;
        }}
        .card:hover {{
            transform: translateY(-6px);
            box-shadow: 0 20px 50px rgba(0,0,0,0.7);
        }}
        .card-ticker {{
            font-family: 'Dela Gothic One', cursive;
            font-size: 52px;
            letter-spacing: -2px;
            line-height: 1;
        }}
        .card-badge {{
            display: inline-block;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1px;
            background: rgba(0,0,0,0.3);
            border-radius: 30px;
            padding: 4px 12px;
            margin-top: 10px;
        }}
        .card-meta {{
            margin-top: 16px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }}
        .meta-item .label {{ font-size: 10px; opacity: 0.5; text-transform: uppercase; letter-spacing: 1px; }}
        .meta-item .val   {{ font-size: 20px; font-weight: 700; margin-top: 2px; }}
        .gain-hit {{ color: var(--green); }}
        .prob-val {{ color: var(--gold); }}

        /* 今日の推薦がない時 */
        .empty-state {{
            text-align: center;
            padding: 80px 0;
            opacity: 0.4;
        }}
        .empty-state .icon {{ font-size: 60px; }}
        .empty-state p {{ margin-top: 16px; font-size: 18px; }}

        .sync-badge {{
            font-size: 12px;
            opacity: 0.4;
            margin-top: 8px;
        }}
    </style>
</head>
<body>
    <header>
        <div>
            <div class="title">📈 AI 当日+1%パトロール</div>
            <div class="subtitle">楽天証券ゼロコース対応 | 始値から当日中に+1%達成を狙う</div>
        </div>
        <div style="text-align:right">
            <div style="font-size:12px;opacity:0.4;letter-spacing:1px;">LAST SYNC</div>
            <div style="font-size:22px;font-weight:900;color:var(--green);">{last_sync_time}</div>
            <div class="sync-badge">120秒ごとに自動更新</div>
        </div>
    </header>

    <div class="kpi-bar">
        <div class="kpi">
            <div class="kpi-label">本日の推薦</div>
            <div class="kpi-value blue">{len(cards) if cards else 0}</div>
        </div>
        <div class="kpi">
            <div class="kpi-label">🎯 達成</div>
            <div class="kpi-value green">{achieved}</div>
        </div>
        <div class="kpi">
            <div class="kpi-label">❌ 未達</div>
            <div class="kpi-value red">{missed}</div>
        </div>
        <div class="kpi">
            <div class="kpi-label">通算勝率</div>
            <div class="kpi-value gold">{win_rate}%</div>
        </div>
        <div class="kpi">
            <div class="kpi-label">平均利益</div>
            <div class="kpi-value green">+{avg_gain}%</div>
        </div>
    </div>

    <div class="grid" id="grid"></div>

    <script>
    const cards = {json_cards};
    const grid = document.getElementById('grid');

    if (cards.length === 0) {{
        grid.innerHTML = `
            <div class="empty-state" style="grid-column:1/-1">
                <div class="icon">🛰️</div>
                <p>本日の推薦銘柄はまだありません。<br>次のスキャン（30分ごと）をお待ちください。</p>
            </div>`;
    }} else {{
        cards.forEach(c => {{
            const el = document.createElement('div');
            el.className = 'card';
            el.style.background = c.grad;

            const gainBlock = c.status === '✅ 達成！'
                ? `<div class="meta-item">
                    <div class="label">達成利益</div>
                    <div class="val gain-hit">${{c.gain_str}}</div>
                   </div>
                   <div class="meta-item">
                    <div class="label">達成時刻</div>
                    <div class="val">${{c.achieved_time}}</div>
                   </div>`
                : `<div class="meta-item">
                    <div class="label">エントリー</div>
                    <div class="val">${{c.entry_price.toLocaleString()}}円</div>
                   </div>
                   <div class="meta-item">
                    <div class="label">推薦時刻</div>
                    <div class="val">${{c.entry_time}}</div>
                   </div>`;

            el.innerHTML = `
                <div class="card-ticker">${{c.ticker}}</div>
                <span class="card-badge">${{c.badge}}</span>
                <div class="card-meta">
                    <div class="meta-item">
                        <div class="label">AI確信度</div>
                        <div class="val prob-val">${{c.win_prob}}%</div>
                    </div>
                    ${{gainBlock}}
                </div>`;
            grid.appendChild(el);
        }});
    }}
    </script>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("✅ ダッシュボードを更新しました。")

if __name__ == "__main__":
    generate_dashboard()
