import pandas as pd
import numpy as np

class BaseStrategy:
    def __init__(self, data):
        self.data = data

    def generate_signals(self, data=None):
        raise NotImplementedError("Subclasses must implement generate_signals()")

class SpecificNewsStrategy(BaseStrategy):
    """
    特定の『キーワード』が含まれるニュースに反応する手法。
    1枚1万円などの小額投資を想定し、ニュース後1週間（5営業日）で売買を完結させる短期単発手法。
    """
    def __init__(self, data, buy_keywords=['決算', '利益', '上方修正', '就任'], sell_keywords=['不正', '停止', '減益', '退任']):
        super().__init__(data)
        self.buy_keywords = buy_keywords
        self.sell_keywords = sell_keywords

    def generate_signals(self, data=None):
        df = data.copy() if data is not None else self.data.copy()
        signals = [0] * len(df)
        
        # 今回の「単発売買」ルール:
        # 1. 指定のキーワードを含むニュースが出たら「買い」
        # 2. その後は保有（5営業日、または悪いニュースが出るまで）
        # 3. 指定の期間が来たら「売り（利益確定/損切り）」
        
        hold_duration = 5 # 5営業日（約1週間）で売る単発ルール
        days_held = 0
        currently_holding = False
        
        for i in range(len(df)):
            news = str(df['News_Event'].iloc[i]) if 'News_Event' in df.columns else ""
            
            # --- 1. ニュースによる買い判断 ---
            is_buy_news = any(kw in news for kw in self.buy_keywords)
            
            if is_buy_news and not currently_holding:
                signals[i] = 1 # 買いサイン
                currently_holding = True
                days_held = 0
                continue
            
            # --- 2. 売り（手仕舞い）判断 ---
            if currently_holding:
                days_held += 1
                is_sell_news = any(kw in news for kw in self.sell_keywords)
                
                # 手放す条件：期間満了 または 悪いニュース発生
                if days_held >= hold_duration or is_sell_news:
                    signals[i] = -1 # 売りサイン
                    currently_holding = False
                    days_held = 0
        
        return signals
