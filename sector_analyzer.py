import pandas as pd
import os

# --- 🛰️ Sniper AI V8.4: Sector Intelligence Engine ---
# 役割: 銘柄をセクター別に分類し、マネーフロー（資金流入）の偏りを分析する。

class SectorAnalyzer:
    def __init__(self, db_file="database.csv"):
        self.db_file = db_file
        # 日本株の主要セクターマッピング (簡易版)
        self.sector_map = {
            "7203.T": "輸送用機器", "7267.T": "輸送用機器",
            "8306.T": "銀行", "8316.T": "銀行",
            "8035.T": "電気機器", "6758.T": "電気機器",
            "8001.T": "卸売", "8058.T": "卸売",
            "9984.T": "情報・通信", "9432.T": "情報・通信"
        }

    def analyze_flow(self):
        if not os.path.exists(self.db_file): return {}
        
        df = pd.read_csv(self.db_file)
        # セクター情報の付与
        df['sector'] = df['ticker'].map(lambda x: self.sector_map.get(x, "その他"))
        
        # セクターごとの平均スコアと騰落率を計算
        sector_stats = df.groupby('sector').agg({
            'score': 'mean',
            'true_ev': 'mean',
            'ticker': 'count'
        }).rename(columns={'ticker': 'count'})
        
        # スコアが高い順にソート
        sector_stats = sector_stats.sort_values(by='score', ascending=False)
        
        return sector_stats.to_dict(orient='index')

if __name__ == "__main__":
    analyzer = SectorAnalyzer()
    flow = analyzer.analyze_flow()
    print(f"Sector Money Flow: {flow}")
