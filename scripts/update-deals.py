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
try:
    import feedparser
except ImportError:
    print("警告: feedparserがインストールされていません。レビュー記事の取得をスキップします。")
    print("インストールするには: pip install feedparser")
    feedparser = None

try:
    from deep_translator import GoogleTranslator
    translator = GoogleTranslator(source='en', target='ja')
except ImportError:
    print("警告: deep-translatorがインストールされていません。英語記事の翻訳をスキップします。")
    print("インストールするには: pip install deep-translator")
    translator = None

def translate_to_japanese(text, max_retries=3):
    """英語テキストを日本語に翻訳"""
    if not translator or not text:
        return text

    try:
        # 長いテキストは分割して翻訳（5000文字以内）
        if len(text) > 5000:
            text = text[:5000]

        # 翻訳実行（リトライ機能付き）
        for attempt in range(max_retries):
            try:
                translated = translator.translate(text)
                return translated
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  翻訳リトライ中... ({attempt + 1}/{max_retries})")
                    import time
                    time.sleep(1)  # 1秒待機
                else:
                    raise e
    except Exception as e:
        print(f"  翻訳エラー: {e}")
        return text  # 翻訳失敗時は元のテキストを返す

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

def fetch_humble_bundle_direct():
    """Humble Bundle公式サイトから直接バンドル情報を取得"""
    try:
        bundles = []
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Humble Bundleのバンドル一覧ページ
        urls = [
            'https://www.humblebundle.com/bundles',
            'https://www.humblebundle.com/games'
        ]

        for url in urls:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()

                # 簡易的なHTMLパース（beautifulsoup4使用）
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # バンドルのタイトルを探す
                    bundle_elements = soup.find_all(['h2', 'h3', 'div'], class_=lambda x: x and ('title' in x.lower() or 'name' in x.lower()))

                    for element in bundle_elements[:3]:
                        title = element.get_text(strip=True)
                        if title and len(title) > 5 and 'bundle' in title.lower():
                            bundles.append({
                                "title": f"{title}",
                                "platform": "Humble Bundle",
                                "type": "bundle",
                                "description": f"Humble Bundleで{title}が登場！複数のゲームがセットになった特別価格。期間限定のお得なバンドルです。",
                                "price": "お得価格",
                                "originalPrice": "",
                                "discount": "",
                                "deadline": "期間限定",
                                "url": "https://www.humblebundle.com/bundles",
                                "date": current_date
                            })
                except ImportError:
                    print("  beautifulsoup4がインストールされていません")

            except Exception as e:
                print(f"  Humble Bundle直接取得エラー: {e}")
                continue

        return bundles[:3]
    except Exception as e:
        print(f"  Humble Bundle情報の取得に失敗: {e}")
        return []

def fetch_isthereanydeal_bundles():
    """IsThereAnyDeal APIからバンドル情報を取得"""
    try:
        bundles = []
        current_date = datetime.now().strftime("%Y-%m-%d")

        # IsThereAnyDeal のバンドル情報（公開API）
        # 注: APIキーが必要な場合があります
        url = "https://isthereanydeal.com/"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                # IsThereAnyDealのページから現在のバンドル情報を取得
                # 実際のAPIエンドポイントがあれば、それを使用する方が良い
                print("  IsThereAnyDeal接続成功")
        except Exception as e:
            print(f"  IsThereAnyDeal接続エラー: {e}")

        return bundles
    except Exception as e:
        print(f"  IsThereAnyDeal情報の取得に失敗: {e}")
        return []

def fetch_reddit_bundles():
    """Redditからバンドル情報を取得"""
    try:
        bundles = []
        current_date = datetime.now().strftime("%Y-%m-%d")

        subreddits = ['GameDeals', 'humblebundles']

        for subreddit in subreddits:
            try:
                url = f"https://www.reddit.com/r/{subreddit}/new.json"
                headers = {'User-Agent': 'GameDealsBot/1.0'}
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()

                if 'data' in data and 'children' in data['data']:
                    for post in data['data']['children'][:15]:
                        post_data = post['data']
                        title = post_data.get('title', '')
                        url_link = post_data.get('url', '')
                        title_lower = title.lower()

                        # バンドルを示すキーワード（拡充）
                        is_bundle = ('bundle' in title_lower or 'バンドル' in title or
                                     'humble choice' in title_lower or
                                     'monthly' in title_lower or
                                     'collection' in title_lower or
                                     'pack' in title_lower and 'game' in title_lower or
                                     'fanatical' in title_lower and 'bundle' in title_lower)

                        if not is_bundle:
                            continue

                        # プラットフォームを検出
                        platform = None
                        platform_url = None
                        bundle_title = title

                        if 'humble' in title_lower:
                            platform = "Humble Bundle"
                            platform_url = url_link if 'humblebundle.com' in url_link else 'https://www.humblebundle.com/'
                        elif 'fanatical' in title_lower:
                            platform = "Fanatical"
                            platform_url = url_link if 'fanatical.com' in url_link else 'https://www.fanatical.com/'
                        elif 'steam' in title_lower:
                            platform = "Steam"
                            platform_url = url_link if 'steampowered.com' in url_link else 'https://store.steampowered.com/'

                        if platform and platform_url:
                            bundles.append({
                                "title": bundle_title,
                                "platform": platform,
                                "type": "bundle",
                                "description": f"{platform}でお得なバンドルが登場！複数のゲームがセットになった特別価格。詳細はリンク先でご確認ください。",
                                "price": "お得価格",
                                "originalPrice": "",
                                "discount": "",
                                "deadline": "期間限定",
                                "url": platform_url,
                                "date": current_date
                            })
            except Exception as e:
                print(f"  Reddit {subreddit}の取得に失敗: {e}")
                continue

        # 重複を削除
        seen_titles = set()
        unique_bundles = []
        for bundle in bundles:
            title_key = bundle['title'].lower()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_bundles.append(bundle)

        return unique_bundles[:5]  # 最大5件まで
    except Exception as e:
        print(f"Redditバンドル情報の取得に失敗: {e}")
        return []

def fetch_reddit_sales():
    """Redditからセール情報を取得"""
    try:
        sales = []
        current_date = datetime.now().strftime("%Y-%m-%d")

        subreddits = ['GameDeals', 'steamdeals']

        for subreddit in subreddits:
            try:
                url = f"https://www.reddit.com/r/{subreddit}/hot.json"
                headers = {'User-Agent': 'GameDealsBot/1.0'}
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()

                if 'data' in data and 'children' in data['data']:
                    for post in data['data']['children'][:15]:
                        post_data = post['data']
                        title = post_data.get('title', '')
                        url_link = post_data.get('url', '')
                        title_lower = title.lower()

                        # セールを示すキーワード（バンドルと無料は除外）
                        is_sale = (('sale' in title_lower or 'セール' in title or
                                    '% off' in title_lower or 'discount' in title_lower or
                                    'deal' in title_lower) and
                                   'bundle' not in title_lower and
                                   'free' not in title_lower and
                                   '100%' not in title)

                        if not is_sale:
                            continue

                        # プラットフォームを検出
                        platform = None
                        platform_url = None

                        if 'steam' in title_lower or 'steampowered.com' in url_link.lower():
                            platform = "Steam"
                            platform_url = url_link if 'steampowered.com' in url_link else 'https://store.steampowered.com/'
                        elif 'epic' in title_lower or 'epicgames.com' in url_link.lower():
                            platform = "Epic Games"
                            platform_url = url_link if 'epicgames.com' in url_link else 'https://store.epicgames.com/'
                        elif 'gog' in title_lower or 'gog.com' in url_link.lower():
                            platform = "GOG"
                            platform_url = url_link if 'gog.com' in url_link else 'https://www.gog.com/'
                        elif 'fanatical' in title_lower:
                            platform = "Fanatical"
                            platform_url = url_link if 'fanatical.com' in url_link else 'https://www.fanatical.com/'
                        elif 'humble' in title_lower:
                            platform = "Humble Bundle"
                            platform_url = url_link if 'humblebundle.com' in url_link else 'https://www.humblebundle.com/'

                        if platform and platform_url:
                            sales.append({
                                "title": title,
                                "platform": platform,
                                "type": "sale",
                                "description": f"{platform}でセール開催中！お得な価格でゲームを入手できるチャンス。詳細はリンク先でご確認ください。",
                                "price": "セール中",
                                "originalPrice": "",
                                "discount": "",
                                "deadline": "期間限定",
                                "url": platform_url,
                                "date": current_date
                            })
            except Exception as e:
                print(f"  Reddit {subreddit}の取得に失敗: {e}")
                continue

        # 重複を削除
        seen_titles = set()
        unique_sales = []
        for sale in sales:
            title_key = sale['title'].lower()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_sales.append(sale)

        return unique_sales[:5]  # 最大5件まで
    except Exception as e:
        print(f"Redditセール情報の取得に失敗: {e}")
        return []

def fetch_review_articles():
    """ゲームメディアのRSSフィードからレビュー記事を取得"""
    if not feedparser:
        print("feedparserがインストールされていないため、レビュー記事の取得をスキップします")
        return []

    try:
        review_articles = []
        current_date = datetime.now().strftime("%Y-%m-%d")

        # レビュー判定キーワード（拡充）
        review_keywords_ja = [
            'レビュー', 'プレビュー', '評価', 'インプレッション', 'プレイレポート',
            'レポート', 'プレイ日記', '先行プレイ', '体験版', 'ハンズオン',
            'プレイ感想', 'インプレ', 'クイックレビュー', 'プレイしてみた'
        ]
        review_keywords_en = [
            'review', 'preview', 'impression', 'hands-on', 'first look',
            'early access', 'playtest', 'gameplay', 'first impression',
            'tested', 'played', 'playing', 'impressions'
        ]

        # ゲーム関連キーワード（ゲームではない記事を除外するため）
        game_keywords_ja = [
            'ゲーム', 'PC版', 'Steam', 'PS5', 'PS4', 'Xbox', 'Switch',
            'リリース', '配信', '発売', 'RPG', 'アクション', 'シミュレーション',
            'ストラテジー', 'アドベンチャー', 'パズル', 'FPS', 'TPS',
            'インディー', 'DLC', 'アップデート', 'タイトル', 'プレイヤー',
            '早期アクセス', 'ベータ'
        ]
        game_keywords_en = [
            'game', 'gaming', 'pc version', 'steam', 'playstation', 'xbox',
            'nintendo', 'switch', 'release', 'launch', 'rpg', 'action',
            'simulation', 'strategy', 'adventure', 'puzzle', 'fps', 'tps',
            'indie', 'dlc', 'update', 'title', 'player', 'early access',
            'beta', 'multiplayer', 'singleplayer'
        ]

        # ハードウェア関連キーワード（除外用）
        hardware_keywords = [
            'cpu', 'gpu', 'graphics card', 'processor', 'motherboard', 'case',
            'cooling', 'corsair', 'nvidia', 'amd', 'intel', 'monitor', 'mouse',
            'keyboard', 'headset', 'ram', 'ssd', 'storage', 'psu', 'power supply',
            'laptop', 'notebook', 'asus', 'tuf gaming', 'alienware', 'razer blade',
            'msi', 'lenovo', 'dell', 'hp omen', 'acer predator', 'router', 'wifi',
            'rtx 30', 'rtx 40', 'rtx 50', 'radeon', 'geforce', 'ryzen', 'core i',
            'cooler', 'fan', 'thermal', 'chassis', 'air 54', 'pc case', 'tower',
            'rgb', 'liquid cooling', 'watercooling', 'gaming chair', 'desk',
            'webcam', 'microphone', 'speakers', 'controller review', 'peripheral'
        ]

        # 各ゲームメディアのRSSフィード
        rss_feeds = [
            {
                'url': 'https://automaton-media.com/feed/',
                'platform': 'AUTOMATON',
                'lang': 'ja'
            },
            {
                'url': 'https://doope.jp/feed',
                'platform': 'doope!',
                'lang': 'ja'
            },
            {
                'url': 'https://www.inside-games.jp/rss/index.xml',
                'platform': 'インサイド',
                'lang': 'ja'
            },
            {
                'url': 'https://www.pcgamer.com/rss/',
                'platform': 'PC Gamer',
                'lang': 'en'
            },
            {
                'url': 'https://www.rockpapershotgun.com/feed',
                'platform': 'Rock Paper Shotgun',
                'lang': 'en'
            },
            {
                'url': 'https://www.polygon.com/rss/index.xml',
                'platform': 'Polygon',
                'lang': 'en'
            }
        ]

        for feed_info in rss_feeds:
            try:
                print(f"  {feed_info['platform']}のRSSフィードを取得中...")
                feed = feedparser.parse(feed_info['url'])

                if not feed.entries:
                    print(f"  {feed_info['platform']}: 記事が見つかりませんでした")
                    continue

                # フィード内の記事をチェック（最新30件に拡大）
                articles_from_this_feed = 0
                for entry in feed.entries[:30]:
                    title = entry.get('title', '')
                    link = entry.get('link', '')
                    summary = entry.get('summary', '') or entry.get('description', '')

                    # HTMLタグを削除
                    summary_clean = re.sub(r'<[^>]+>', '', summary)[:300]

                    # タイトルと要約を検索対象に
                    title_lower = title.lower()
                    summary_lower = summary_clean.lower()
                    full_text_lower = f"{title_lower} {summary_lower}"

                    # ハードウェアレビューを除外（タイトルと要約の両方をチェック）
                    is_hardware = any(hw in full_text_lower for hw in hardware_keywords)
                    if is_hardware:
                        print(f"    ✗ ハードウェアレビューを除外: {title[:40]}...")
                        continue

                    # レビュー関連のキーワードチェック（タイトルまたは要約）
                    is_review = False
                    if feed_info['lang'] == 'ja':
                        is_review = any(keyword in title or keyword in summary_clean for keyword in review_keywords_ja)
                    else:
                        is_review = any(keyword in full_text_lower for keyword in review_keywords_en)

                    # ゲーム関連かチェック（より緩い判定）
                    is_game_related = False
                    if feed_info['lang'] == 'ja':
                        is_game_related = any(keyword in title or keyword in summary_clean for keyword in game_keywords_ja)
                    else:
                        is_game_related = any(keyword in full_text_lower for keyword in game_keywords_en)

                    # レビュー記事かつゲーム関連の場合のみ追加
                    # ただし、ゲーム専門メディア（AUTOMATON、doope!など）の場合は
                    # レビューキーワードがあれば基本的にゲーム関連と判断
                    game_focused_media = ['AUTOMATON', 'doope!', 'インサイド', 'Rock Paper Shotgun', 'Polygon']

                    if is_review and link:
                        if feed_info['platform'] in game_focused_media or is_game_related:
                            # 英語記事は自動翻訳
                            if feed_info['lang'] == 'en':
                                # タイトルを翻訳
                                print(f"    翻訳中: {title[:40]}...")
                                translated_title = translate_to_japanese(title)

                                # 説明文を翻訳
                                if summary_clean:
                                    translated_summary = translate_to_japanese(summary_clean)
                                    description = translated_summary
                                else:
                                    description = f"{translated_title}の詳細記事です。"

                                # 翻訳されたタイトルを使用
                                title = translated_title
                            else:
                                # 日本語記事はそのまま
                                description = summary_clean if summary_clean else f"{title}の詳細記事です。"

                            review_articles.append({
                                "title": title,
                                "platform": feed_info['platform'],
                                "type": "review",
                                "description": description,
                                "price": "",
                                "originalPrice": "",
                                "discount": "",
                                "deadline": "",
                                "url": link,
                                "date": current_date
                            })

                            articles_from_this_feed += 1
                            print(f"    ✓ レビュー記事を発見: {title[:50]}...")

                            # 各フィードから最大3件まで（2件→3件に拡大）
                            if articles_from_this_feed >= 3:
                                break

                if articles_from_this_feed == 0:
                    print(f"  {feed_info['platform']}: レビュー記事が見つかりませんでした")

            except Exception as e:
                print(f"  {feed_info['platform']}のRSS取得エラー: {e}")
                import traceback
                traceback.print_exc()
                continue

        print(f"\n合計 {len(review_articles)} 件のレビュー記事を取得しました")

        # 新しい順にソートして最新15件を返す（10件→15件に拡大）
        review_articles.sort(key=lambda x: x['date'], reverse=True)
        return review_articles[:15]

    except Exception as e:
        print(f"レビュー記事の取得に失敗: {e}")
        import traceback
        traceback.print_exc()
        return []

def update_games_data():
    """games-data.jsonを更新"""
    try:
        # 既存のデータを読み込み
        with open('games-data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 各ソースから情報を取得
        print("\n🎮 無料ゲーム情報を取得中...")
        epic_games = fetch_epic_free_games()
        reddit_games = fetch_reddit_free_games()

        print("\n📦 バンドル情報を取得中...")
        # 複数のソースからバンドル情報を取得
        reddit_bundles = fetch_reddit_bundles()
        humble_bundles = fetch_humble_bundle_direct()
        itad_bundles = fetch_isthereanydeal_bundles()

        # 全てのバンドル情報を統合
        all_bundles = reddit_bundles + humble_bundles + itad_bundles

        # 重複を削除
        seen_titles = set()
        reddit_bundles = []
        for bundle in all_bundles:
            title_key = bundle.get('title', '').lower()
            if title_key and title_key not in seen_titles:
                seen_titles.add(title_key)
                reddit_bundles.append(bundle)

        reddit_count = len(all_bundles) - len(humble_bundles) - len(itad_bundles)
        print(f"  取得したバンドル情報: Reddit={reddit_count}件, "
              f"Humble Bundle={len(humble_bundles)}件, IsThereAnyDeal={len(itad_bundles)}件, 合計={len(reddit_bundles)}件")

        print("\n🔥 セール情報を取得中...")
        reddit_sales = fetch_reddit_sales()

        print("\n📰 レビュー記事を取得中...")
        review_articles = fetch_review_articles()

        total_new_games = len(epic_games) + len(reddit_games)

        if total_new_games > 0:
            print(f"\n✨ 合計{total_new_games}件の新しい無料ゲーム情報を取得しました")
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

        # レビュー記事を更新
        if review_articles:
            print(f"\n📚 {len(review_articles)}件のレビュー記事を取得しました")
            for article in review_articles:
                print(f"  - {article['title'][:50]}... ({article['platform']})")

            # reviewカテゴリが存在しない場合は作成
            if 'review' not in data['pc']:
                data['pc']['review'] = []

            # 既存のレビュー記事と新規記事をマージ（重複削除）
            # 手動で追加された記事（日付が1週間以上前のもの）は保持
            current_date = datetime.now()
            manual_reviews = []
            for review in data['pc']['review']:
                try:
                    review_date = datetime.strptime(review.get('date', ''), "%Y-%m-%d")
                    days_old = (current_date - review_date).days
                    # 7日以上前の記事は手動追加と見なして保持
                    if days_old >= 7:
                        manual_reviews.append(review)
                except (ValueError, TypeError):
                    # 日付がパースできない場合は手動追加と見なして保持
                    manual_reviews.append(review)

            # 新規記事と手動追加記事を結合
            all_reviews = review_articles + manual_reviews

            # 重複を削除（URLベース）
            seen_urls = set()
            unique_reviews = []
            for review in all_reviews:
                url = review.get('url', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_reviews.append(review)

            # 最新15件を保持（より多くのレビュー記事を表示）
            data['pc']['review'] = unique_reviews[:15]

        # バンドル情報を更新
        if reddit_bundles:
            print(f"\n📦 {len(reddit_bundles)}件のバンドル情報を取得しました")
            for bundle in reddit_bundles:
                print(f"  - {bundle['title'][:50]}... ({bundle['platform']})")

            # bundleカテゴリが存在しない場合は作成
            if 'bundle' not in data['pc']:
                data['pc']['bundle'] = []

            # 自動取得された古いバンドル情報を削除（14日以上前）
            # バンドルは通常2-4週間続くため、より長く保持する
            data['pc']['bundle'] = clean_old_free_games(data['pc']['bundle'], max_age_days=14)

            # 新しい情報を先頭に追加
            data['pc']['bundle'] = reddit_bundles + data['pc']['bundle']

            # 重複を削除（タイトルベース）
            seen_titles = set()
            unique_bundles = []
            for bundle in data['pc']['bundle']:
                title_key = bundle.get('title', '').lower()
                if title_key not in seen_titles:
                    seen_titles.add(title_key)
                    unique_bundles.append(bundle)

            # 最新15件を保持（より多くのバンドル情報を表示）
            data['pc']['bundle'] = unique_bundles[:15]

        # セール情報を更新
        if reddit_sales:
            print(f"\n🔥 {len(reddit_sales)}件のセール情報を取得しました")
            for sale in reddit_sales:
                print(f"  - {sale['title'][:50]}... ({sale['platform']})")

            # saleカテゴリが存在しない場合は作成
            if 'sale' not in data['pc']:
                data['pc']['sale'] = []

            # 自動取得された古いセール情報を削除（7日以上前）
            data['pc']['sale'] = clean_old_free_games(data['pc']['sale'], max_age_days=7)

            # 新しい情報を先頭に追加
            data['pc']['sale'] = reddit_sales + data['pc']['sale']

            # 重複を削除（タイトルベース）
            seen_titles = set()
            unique_sales = []
            for sale in data['pc']['sale']:
                title_key = sale.get('title', '').lower()
                if title_key not in seen_titles:
                    seen_titles.add(title_key)
                    unique_sales.append(sale)

            # 最新10件を保持
            data['pc']['sale'] = unique_sales[:10]

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
