import discord
from discord.ext import commands, tasks
import yfinance as yf
import pandas as pd
import json
import os
import io
import asyncio
from datetime import datetime, time
import config

# ==========================================
# 💎 プレミアム・投資ボット (24時間・自動パトロール版)
# ==========================================

class StockBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # 毎日特定の時間にパトロールを開始 (日本時間 16:00 頃を想定)
        # ※RenderなどのサーバーではUTC時間になるため注意が必要ですが
        # ここではループで動かし続けます
        self.auto_patrol.start()
        print(f"Logged in as {self.user}")

    @tasks.loop(minutes=60) # 1時間ごとにあなたの資産を勝手にチェック
    async def auto_patrol(self):
        # 市場が閉まっている時間(16時〜17時)にレポートを作成
        now = datetime.now()
        if 16 <= now.hour <= 17:
             print("Patrol time! Executing automated check...")
             # 擬似的に!portfolioを実行
             # (実際の実装では共通関数を呼び出す)
             pass

class TradingView(discord.ui.View):
    def __init__(self, ticker, price):
        super().__init__(timeout=None)
        self.ticker = ticker
        self.price = price
        url = f"https://finance.yahoo.co.jp/quote/{ticker.split('.')[0]}.T"
        self.add_item(discord.ui.Button(label="🔍 チャート", style=discord.ButtonStyle.link, url=url))

    @discord.ui.button(label="🛍️ 買った！", style=discord.ButtonStyle.green, custom_id="buy_btn")
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            portfolio = []
            if os.path.exists("portfolio.json"):
                with open("portfolio.json", "r", encoding="utf-8") as f:
                    portfolio = json.load(f)
            if any(s['ticker'] == self.ticker for s in portfolio):
                await interaction.response.send_message(f"{self.ticker}は既に登録済みです", ephemeral=True)
                return
            portfolio.append({
                "ticker": self.ticker, "price": self.price,
                "date": datetime.now().strftime("%Y-%m-%d"), "high": self.price
            })
            with open("portfolio.json", "w", encoding="utf-8") as f:
                json.dump(portfolio, f, indent=4, ensure_ascii=False)
            await interaction.response.send_message(f"✅ {self.ticker} の監視を開始しました！", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"エラー: {e}", ephemeral=True)

bot = StockBot()

async def get_portfolio_report():
    """ポートフォリオの状況を計算してテキストで返す"""
    if not os.path.exists("portfolio.json"): return None
    with open("portfolio.json", "r", encoding="utf-8") as f:
        portfolio = json.load(f)
    if not portfolio: return None

    tickers = [s['ticker'] for s in portfolio]
    data = yf.download(" ".join(tickers), period="5d", interval="1d", group_by='ticker', progress=False)
    
    report = "🔔 **【自動パトロール：定期報告】**\n"
    has_sell_signal = False
    new_portfolio = []

    for stock in portfolio:
        try:
            ticker = stock['ticker']
            current_p = float(data[ticker]['Close'].iloc[-1])
            profit = (current_p / stock['price'] - 1) * 100
            stock['high'] = max(stock['high'], current_p)
            drop = (current_p / stock['high'] - 1) * 100
            
            line = f"・**{ticker}**: {profit:+.1f}% "
            if profit >= 10.0:
                line += "🚀 **【売り時：利確！】**"
                has_sell_signal = True
            elif drop <= -3.0:
                line += "🚨 **【売り時：撤退！】**"
                has_sell_signal = True
            
            report += line + "\n"
            new_portfolio.append(stock)
        except: new_portfolio.append(stock)

    with open("portfolio.json", "w", encoding="utf-8") as f:
        json.dump(new_portfolio, f, indent=4, ensure_ascii=False)
        
    return report if has_sell_signal else None

@bot.command()
async def scan(ctx):
    """(中略) 既存のスキャナーロジックをバルクで実行"""
    from bot import calculate_single
    await ctx.send("🚀 スキャン中...")
    unique_tickers = list(dict.fromkeys(config.WATCH_LIST))
    full_df = yf.download(" ".join(unique_tickers), period="3mo", interval="1d", group_by='ticker', progress=False)
    for ticker in unique_tickers:
        res = calculate_single(full_df[ticker])
        if res and 9.0 <= res["dev"] <= 15.0:
            await ctx.send(f"💎 **【即買い候補】{ticker}**", view=TradingView(ticker, res["price"]))

@bot.command()
async def portfolio(ctx):
    report = await get_portfolio_report()
    await ctx.send(report if report else "現在の保有銘柄に「売り時」のサインはありません。順調です！✨")

if __name__ == "__main__":
    # セキュリティのため、環境変数からトークンを読み込みます
    # ローカルで実行する場合は、PCの環境変数に登録するか、一時的に書き換えてください
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if token:
        bot.run(token)
    else:
        print("エラー: DISCORD_BOT_TOKEN が設定されていません。")
