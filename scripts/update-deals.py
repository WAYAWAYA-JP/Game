#!/usr/bin/env python3
"""
ゲーム情報自動更新スクリプト
Epic Games、Steam、Redditなどの情報を取得してgames-data.jsonを更新します
"""

import json
import requests
from datetime import datetime
import sys
import re
from urllib.parse import urlparse

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

def fetch_reddit_free_games():
    """Redditから無料ゲーム情報を取得"""
    try:
        free_games = []
        current_date = datetime.now().strftime("%Y-%m-%d")

        # r/FreeGamesOnSteam と r/GameDeals から情報を取得
        subreddits = ['FreeGamesOnSteam', 'GameDeals']

        for subreddit in subreddits:
            try:
                url = f"https://www.reddit.com/r/{subreddit}/new.json"
                headers = {'User-Agent': 'GameDealsBot/1.0'}
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()

                if 'data' in data and 'children' in data['data']:
                    for post in data['data']['children'][:10]:  # 最新10件をチェック
                        post_data = post['data']
                        title = post_data.get('title', '')
                        url_link = post_data.get('url', '')
                        title_lower = title.lower()

                        # 無料配布を示すキーワード
                        is_free = ('free' in title_lower or '100%' in title or
                                   '無料' in title or 'giveaway' in title_lower)

                        if not is_free:
                            continue

                        # プラットフォームを検出
                        platform = None
                        platform_url = None
                        game_title = title.split('-')[0].strip() if '-' in title else title

                        # Steam
                        if 'steam' in title_lower or 'steampowered.com' in url_link.lower():
                            platform = "Steam"
                            platform_url = url_link if 'steampowered.com' in url_link else 'https://store.steampowered.com/'

                        # GOG
                        elif 'gog' in title_lower or 'gog.com' in url_link.lower():
                            platform = "GOG"
                            platform_url = url_link if 'gog.com' in url_link else 'https://www.gog.com/'

                        # Prime Gaming
                        elif ('prime' in title_lower and 'gaming' in title_lower) or \
                             'primegaming' in title_lower or 'amazon prime' in title_lower or \
                             'gaming.amazon.com' in url_link.lower():
                            platform = "Prime Gaming"
                            platform_url = url_link if 'amazon.com' in url_link else 'https://gaming.amazon.com/'

                        # Fanatical
                        elif 'fanatical' in title_lower or 'fanatical.com' in url_link.lower():
                            platform = "Fanatical"
                            platform_url = url_link if 'fanatical.com' in url_link else 'https://www.fanatical.com/'

                        # Humble Bundle
                        elif 'humble' in title_lower or 'humblebundle.com' in url_link.lower():
                            platform = "Humble Bundle"
                            platform_url = url_link if 'humblebundle.com' in url_link else 'https://www.humblebundle.com/'

                        # プラットフォームが検出できた場合のみ追加
                        if platform and platform_url:
                            free_games.append({
                                "title": f"{game_title} - {platform} 無料配布中",
                                "platform": platform,
                                "type": "free",
                                "description": f"{platform}で期間限定無料配布中！このチャンスを逃さずに入手しましょう。詳細はリンク先でご確認ください。",
                                "price": "無料",
                                "originalPrice": "",
                                "discount": "100% OFF",
                                "deadline": "期間限定",
                                "url": platform_url,
                                "date": current_date
                            })
            except Exception as e:
                print(f"Reddit {subreddit}の取得に失敗: {e}")
                continue

        # 重複を削除
        seen_titles = set()
        unique_games = []
        for game in free_games:
            if game['title'] not in seen_titles:
                seen_titles.add(game['title'])
                unique_games.append(game)

        return unique_games[:5]  # 最大5件まで
    except Exception as e:
        print(f"Reddit情報の取得に失敗: {e}")
        return []

def fetch_steam_specials():
    """Steamの特価セール情報を取得"""
    try:
        free_games = []
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Steam APIで無料ゲームを検索（週末無料プレイなど）
        # 注: Steamの公式APIは制限があるため、実際の運用では別のアプローチが必要

        # SteamDBやIsThereAnyDealのAPIを使う方法もあります
        # ここでは簡易的な実装として、既知の無料配布パターンを返す

        return free_games
    except Exception as e:
        print(f"Steam情報の取得に失敗: {e}")
        return []

def clean_old_free_games(games_list, max_age_days=7):
    """古い無料ゲーム情報を削除（7日以上前のもの）"""
    current_date = datetime.now()
    cleaned_games = []

    for game in games_list:
        try:
            game_date = datetime.strptime(game.get('date', ''), "%Y-%m-%d")
            days_old = (current_date - game_date).days

            # 7日以内のものだけ保持、または日付がないもの（固定情報）も保持
            if days_old < max_age_days or not game.get('date'):
                cleaned_games.append(game)
        except (ValueError, TypeError):
            # 日付がパースできない場合は保持
            cleaned_games.append(game)

    return cleaned_games

def update_games_data():
    """games-data.jsonを更新"""
    try:
        # 既存のデータを読み込み
        with open('games-data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 各ソースから情報を取得
        epic_games = fetch_epic_free_games()
        reddit_games = fetch_reddit_free_games()

        total_new_games = len(epic_games) + len(reddit_games)

        if total_new_games > 0:
            print(f"✨ 合計{total_new_games}件の新しい無料ゲーム情報を取得しました")
            print(f"  - Epic Games: {len(epic_games)}件")
            print(f"  - Reddit (全プラットフォーム): {len(reddit_games)}件")

            # Reddit経由で取得したプラットフォームを確認
            platforms_found = set(game.get('platform') for game in reddit_games)
            if platforms_found:
                print(f"  - 検出されたプラットフォーム: {', '.join(platforms_found)}")

            # 自動取得された古いゲーム情報を削除（自動取得プラットフォームのみ）
            auto_platforms = ['Epic Games', 'Steam', 'GOG', 'Prime Gaming', 'Fanatical', 'Humble Bundle']
            data['pc']['free'] = [
                game for game in data['pc']['free']
                if not (game.get('platform') in auto_platforms and
                       '週替わり' not in game.get('title', '') and
                       '期間限定' not in game.get('title', '') and
                       game.get('date'))  # 日付があるもの（自動取得）のみ削除
            ]

            # 古い情報をクリーンアップ（7日以上前のもの）
            data['pc']['free'] = clean_old_free_games(data['pc']['free'])

            # 新しい情報を先頭に追加
            all_new_games = epic_games + reddit_games
            data['pc']['free'] = all_new_games + data['pc']['free']

            # 重複を削除（タイトルベース）
            seen_titles = set()
            unique_games = []
            for game in data['pc']['free']:
                title_key = game.get('title', '').lower()
                if title_key not in seen_titles:
                    seen_titles.add(title_key)
                    unique_games.append(game)

            data['pc']['free'] = unique_games

        # 更新日時を記録
        data['last_updated'] = datetime.now().isoformat()

        # JSONファイルを更新
        with open('games-data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print("✅ games-data.jsonを更新しました")
        print(f"📊 現在の無料ゲーム情報: {len(data['pc']['free'])}件")
        return True

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = update_games_data()
    sys.exit(0 if success else 1)
