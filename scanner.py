import yfinance as yf
import pandas as pd
import numpy as np
import requests
import json
import os
from datetime import datetime
import config

# ==========================================
# 最終進化形：100銘柄トリプル・エンジン(ニュース+黄金パラメータ+ポートフォリオ監視)
# ==========================================

def calculate_gold_indicators(df):
    if len(df) < 25: return None
    
    # 指標計算
    close = df['Close']
    sma25 = close.rolling(window=25).mean()
    df['Dev'] = (close / sma25 - 1) * 100
    
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, np.nan)).fillna(0)))
    df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(window=20).mean()
    df['Is_Green'] = close > df['Open']
    
    return df

def check_news(ticker):
    try:
        stock = yf.Ticker(ticker)
        news_items = stock.news
        if not news_items: return None
        for item in news_items:
            title = item['title']
            if any(kw in title for kw in config.TARGET_KEYWORDS):
                return title
        return None
    except: return None

def scan_for_opportunities():
    """
    ステップ1: 新しい『お宝チャンス』を探す (買いシグナル)
    """
    print(f"\n--- スキャン開始: {datetime.now().strftime('%Y-%M-%d %H:%M')} ---")
    signals = []

    for ticker in config.WATCH_LIST:
        print(f"Analyzing {ticker}...", end="\r")
        try:
            df = yf.download(ticker, period="3mo", interval="1d", progress=False)
            if df.empty: continue
            df = calculate_gold_indicators(df)
            if df is None: continue
            
            last = df.iloc[-1]
            # --- 今回発見した『黄金条件』：乖離率 +9〜12%、RSI 40〜50 ---
            dev = float(last['Dev'])
            rsi = float(last['RSI'])
            vol = float(last['Vol_Ratio'])
            
            # 条件判定
            is_gold_param = (9.0 <= dev <= 15.0) and (35 <= rsi <= 55)
            is_vol_surge = vol > 1.2
            is_green = bool(last['Is_Green'])
            
            if (is_gold_param or is_vol_surge) and is_green:
                news_title = check_news(ticker)
                # ニュースがあれば『ダイヤモンド銘柄』、なければ『テクニカル銘柄』として通知
                type_label = "💎 ダイアモンド(ニュース有)" if news_title else "📈 テクニカル(パラメータ有)"
                signals.append({
                    'type': type_label,
                    'ticker': ticker,
                    'price': float(last['Close']),
                    'news': news_title if news_title else "なし(純粋なチャート買い)"
                })
        except: continue
    return signals

def monitor_portfolio():
    """
    ステップ2: 保有している銘柄の『売り時』を判定する (売りシグナル)
    """
    sell_alerts = []
    try:
        with open("portfolio.json", "r", encoding="utf-8") as f:
            portfolio = json.load(f)
    except: return []

    for stock in portfolio:
        ticker = stock['ticker']
        print(f"Monitoring {ticker}...", end="\r")
        try:
            df = yf.download(ticker, period="1mo", interval="1d", progress=False)
            if df.empty: continue
            current_p = float(df['Close'].iloc[-1])
            entry_p = stock['entry_price']
            ret = (current_p / entry_p - 1) * 100
            
            # 1. 利確チェック (10.0%目標)
            if ret >= stock.get('target_profit_pct', 10.0):
                sell_alerts.append(f"🎉 **【利確チャンス】** {ticker} が目標の+{ret:.1f}%に到達！利益確定を検討してください。")
            
            # 2. 損切チェック (3.0%下落)
            elif ret <= -stock.get('stop_loss_pct', 3.0):
                sell_alerts.append(f"⚠️ **【損切り警告】** {ticker} が-{abs(ret):.1f}%まで下落しました。リスク回避のため撤退を検討してください。")
            
            # 3. RSI天井チェック (75以上で過熱)
            # (RSI計算が必要)
        except: continue
    
    return sell_alerts

def notify(signals, alerts):
    content = ""
    if alerts:
        content += "🚨 **【売り時のお知らせ：ポートフォリオ監視】** 🚨\n" + "\n".join(alerts) + "\n\n"
    
    if signals:
        content += "🚀 **【今日のお宝買いチャンス】** 🚀\n"
        for s in signals:
            content += f"**{s['ticker']}** ({s['type']})\n- 価格: {s['price']:,.0f}円\n- 根拠: {s['news']}\n"
    
    if not content:
        content = "本日は売買すべき特別なシグナルはありませんでした。"
        
    print(content)
    if config.DISCORD_WEBHOOK_URL != "YOUR_WEBHOOK_URL":
        requests.post(config.DISCORD_WEBHOOK_URL, json={"content": content})

if __name__ == "__main__":
    new_buys = scan_for_opportunities()
    sell_signals = monitor_portfolio()
    notify(new_buys, sell_signals)
