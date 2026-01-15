#!/usr/bin/env python3
"""
ゲーム情報自動更新スクリプト
Epic Games、Steamなどの情報を取得してgames-data.jsonを更新します
"""

import json
import requests
from datetime import datetime
import sys

def fetch_epic_free_games():
    """Epic Gamesの無料ゲーム情報を取得"""
    try:
        url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
        params = {
            "locale": "ja",
            "country": "JP",
            "allowCountries": "JP"
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        free_games = []
        current_date = datetime.now().strftime("%Y-%m-%d")

        if 'data' in data and 'Catalog' in data['data']:
            for game in data['data']['Catalog']['searchStore']['elements']:
                # 現在無料配布中のゲームをチェック
                if game.get('promotions'):
                    promotions = game['promotions'].get('promotionalOffers', [])
                    if promotions and len(promotions) > 0:
                        title = game.get('title', 'Unknown')
                        description = game.get('description', '')

                        # 価格情報
                        original_price = "不明"
                        if game.get('price') and game['price'].get('totalPrice'):
                            price_info = game['price']['totalPrice']
                            original_price = f"¥{price_info.get('originalPrice', 0):,}"

                        free_games.append({
                            "title": f"{title} - Epic Games 無料配布中",
                            "platform": "Epic Games",
                            "type": "free",
                            "description": description[:200] if description else f"{title}が期間限定で無料配布中！今すぐ入手して永久にライブラリに追加しよう。",
                            "price": "無料",
                            "originalPrice": original_price,
                            "discount": "100% OFF",
                            "deadline": "期間限定",
                            "url": "https://store.epicgames.com/ja/free-games",
                            "date": current_date
                        })

        return free_games
    except Exception as e:
        print(f"Epic Games情報の取得に失敗: {e}")
        return []

def update_games_data():
    """games-data.jsonを更新"""
    try:
        # 既存のデータを読み込み
        with open('games-data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Epic Gamesの無料ゲーム情報を取得
        epic_games = fetch_epic_free_games()

        if epic_games:
            print(f"Epic Gamesから{len(epic_games)}件の無料ゲーム情報を取得しました")

            # 既存のEpic Games情報を削除して新しい情報を追加
            data['pc']['free'] = [
                game for game in data['pc']['free']
                if game.get('platform') != 'Epic Games' or '週替わり' in game.get('title', '')
            ]

            # 新しい情報を先頭に追加
            data['pc']['free'] = epic_games + data['pc']['free']

        # 更新日時を記録
        data['last_updated'] = datetime.now().isoformat()

        # JSONファイルを更新
        with open('games-data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print("✅ games-data.jsonを更新しました")
        return True

    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

if __name__ == "__main__":
    success = update_games_data()
    sys.exit(0 if success else 1)
