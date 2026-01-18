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
import os

try:
    from dotenv import load_dotenv
    load_dotenv()  # .envファイルから環境変数を読み込み
except ImportError:
    print("警告: python-dotenvがインストールされていません")

try:
    import feedparser
except ImportError:
    print("警告: feedparserがインストールされていません。レビュー記事の取得をスキップします。")
    print("インストールするには: pip install feedparser")
    feedparser = None

# Google翻訳の初期化（deep-translator使用）
try:
    from deep_translator import GoogleTranslator
    translator = GoogleTranslator(source='en', target='ja')
    print("✅ Google翻訳を初期化しました（無料・APIキー不要）")
except ImportError:
    print("警告: deep-translatorパッケージがインストールされていません。翻訳をスキップします。")
    print("インストールするには: pip install deep-translator")
    translator = None
except Exception as e:
    print(f"警告: Google翻訳初期化エラー: {e}")
    translator = None

# Groq APIの初期化（オプション：記事の説明文を生成）
groq_client = None
try:
    from groq import Groq
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    if GROQ_API_KEY:
        groq_client = Groq(api_key=GROQ_API_KEY)
        print("✅ Groq API接続成功（記事説明文生成に使用）")
    else:
        print("ℹ️  GROQ_API_KEY未設定。デフォルトの説明文を使用します。")
except ImportError:
    print("ℹ️  groqパッケージ未インストール。記事説明文はデフォルトを使用します。")
except Exception as e:
    print(f"警告: Groq API初期化エラー: {e}")
    groq_client = None

def clean_reddit_meta(text):
    """Redditのメタ情報を削除"""
    if not text:
        return ""

    # HTMLタグを削除
    text = re.sub(r'<[^>]+>', '', text)

    # "submitted by /u/..." 以降を削除
    text = re.sub(r'submitted by /u/\S+.*', '', text, flags=re.IGNORECASE)

    # [link], [comments] などを削除
    text = re.sub(r'\[link\]|\[comments\]', '', text, flags=re.IGNORECASE)

    # 複数の空白を1つに
    text = re.sub(r'\s+', ' ', text)

    return text.strip()

def generate_description_with_ai(title, platform, deal_type="sale"):
    """Groq APIを使ってタイトルから説明文を生成（失敗時はデフォルト説明文）"""
    if not groq_client:
        # Groq APIが利用できない場合はデフォルトの説明文
        if deal_type == "sale":
            return f"{platform}でお得なセールが開催中！期間限定の特別価格でゲームを手に入れるチャンス。"
        else:
            return f"{platform}でお得なバンドルが登場！複数のゲームがセットでお買い得。"

    try:
        # Groq APIで説明文を生成
        prompt = f"""以下のゲーム{'セール' if deal_type == 'sale' else 'バンドル'}のタイトルから、魅力的な紹介文を日本語で1-2文で生成してください。
ゲーマー向けに、簡潔でわかりやすく、ワクワクする文章にしてください。

プラットフォーム: {platform}
タイトル: {title}

紹介文のみを出力してください（説明や注釈は不要）。"""

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # 高品質で無料枠が広いモデル
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=150
        )

        description = response.choices[0].message.content.strip()
        return description if description else (
            f"{platform}でお得な{'セール' if deal_type == 'sale' else 'バンドル'}が開催中！"
        )

    except Exception as e:
        print(f"  AI説明文生成エラー: {e}")
        # エラー時はデフォルト説明文
        if deal_type == "sale":
            return f"{platform}でお得なセールが開催中！期間限定の特別価格でゲームを手に入れるチャンス。"
        else:
            return f"{platform}でお得なバンドルが登場！複数のゲームがセットでお買い得。"

def translate_to_japanese(text, max_retries=3):
    """Google翻訳で英語テキストを日本語に翻訳"""
    if not translator or not text:
        return text

    try:
        # 長いテキストは分割して翻訳（Google翻訳は5000文字まで）
        if len(text) > 5000:
            text = text[:5000]

        # 翻訳実行（リトライ機能付き）
        import time
        for attempt in range(max_retries):
            try:
                # Google翻訳で翻訳
                translated_text = translator.translate(text)
                # 成功時は少し待機（過負荷防止）
                time.sleep(0.3)
                return translated_text
            except Exception as e:
                error_msg = str(e)
                error_type = type(e).__name__

                if attempt < max_retries - 1:
                    wait_time = 2 * (attempt + 1)  # 2秒, 4秒, 6秒
                    print(f"  翻訳エラー ({error_type})。{wait_time}秒待機後リトライ... ({attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    raise e
    except Exception as e:
        print(f"  翻訳エラー ({type(e).__name__}): {e}")
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

def fetch_fanatical_bundles():
    """Fanatical公式サイトからバンドル情報を取得"""
    try:
        bundles = []
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Fanaticalのバンドル一覧ページ
        url = "https://www.fanatical.com/en/bundles"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            # BeautifulSoupでHTMLをパース
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')

                # Fanaticalのバンドルタイトルを探す
                # 一般的なクラス名やタグで検索
                bundle_elements = soup.find_all(['h2', 'h3', 'div', 'span'],
                                               class_=lambda x: x and any(keyword in str(x).lower()
                                               for keyword in ['bundle', 'title', 'name', 'product']))

                found_bundles = set()
                for element in bundle_elements[:20]:
                    title = element.get_text(strip=True)
                    # バンドルらしいタイトルを検出
                    if (title and len(title) > 10 and len(title) < 150 and
                        ('bundle' in title.lower() or 'collection' in title.lower() or
                         'pack' in title.lower()) and
                        title not in found_bundles):

                        found_bundles.add(title)
                        bundles.append({
                            "title": f"{title}",
                            "platform": "Fanatical",
                            "type": "bundle",
                            "description": f"Fanaticalで{title}が登場！複数のゲームがセットになったお得なバンドル。Steamキーで提供されます。",
                            "price": "お得価格",
                            "originalPrice": "",
                            "discount": "",
                            "deadline": "期間限定",
                            "url": "https://www.fanatical.com/en/bundles",
                            "date": current_date
                        })

                        if len(bundles) >= 5:
                            break

                print(f"  Fanaticalから{len(bundles)}件のバンドルを取得")

            except ImportError:
                print("  beautifulsoup4がインストールされていません")

        except Exception as e:
            print(f"  Fanatical取得エラー: {e}")

        return bundles[:5]
    except Exception as e:
        print(f"  Fanatical情報の取得に失敗: {e}")
        return []

def fetch_indiegala_bundles():
    """IndieGalaからバンドル情報を取得"""
    try:
        bundles = []
        current_date = datetime.now().strftime("%Y-%m-%d")

        # IndieGalaのバンドルページ
        url = "https://www.indiegala.com/bundles"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')

                # バンドルタイトルを探す
                bundle_elements = soup.find_all(['h2', 'h3', 'div', 'a'],
                                               class_=lambda x: x and any(keyword in str(x).lower()
                                               for keyword in ['bundle', 'title', 'name']))

                found_bundles = set()
                for element in bundle_elements[:20]:
                    title = element.get_text(strip=True)
                    if (title and len(title) > 10 and len(title) < 150 and
                        ('bundle' in title.lower() or 'collection' in title.lower()) and
                        title not in found_bundles):

                        found_bundles.add(title)
                        bundles.append({
                            "title": f"{title}",
                            "platform": "IndieGala",
                            "type": "bundle",
                            "description": f"IndieGalaで{title}が登場！インディーゲームを中心としたお得なバンドル。",
                            "price": "お得価格",
                            "originalPrice": "",
                            "discount": "",
                            "deadline": "期間限定",
                            "url": "https://www.indiegala.com/bundles",
                            "date": current_date
                        })

                        if len(bundles) >= 3:
                            break

                print(f"  IndieGalaから{len(bundles)}件のバンドルを取得")

            except ImportError:
                print("  beautifulsoup4がインストールされていません")

        except Exception as e:
            print(f"  IndieGala取得エラー: {e}")

        return bundles[:3]
    except Exception as e:
        print(f"  IndieGala情報の取得に失敗: {e}")
        return []

def fetch_itchio_bundles():
    """Itch.ioからバンドル情報を取得"""
    try:
        bundles = []
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Itch.ioのバンドルページ
        url = "https://itch.io/bundles"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')

                # バンドルタイトルを探す
                bundle_elements = soup.find_all(['h2', 'h3', 'a'],
                                               class_=lambda x: x and 'title' in str(x).lower())

                found_bundles = set()
                for element in bundle_elements[:15]:
                    title = element.get_text(strip=True)
                    if (title and len(title) > 10 and len(title) < 150 and
                        title not in found_bundles and
                        not any(skip in title.lower() for skip in ['browse', 'login', 'register'])):

                        found_bundles.add(title)
                        bundles.append({
                            "title": f"{title}",
                            "platform": "Itch.io",
                            "type": "bundle",
                            "description": f"Itch.ioで{title}が登場！インディーゲーム開発者を支援するバンドル。",
                            "price": "お得価格",
                            "originalPrice": "",
                            "discount": "",
                            "deadline": "期間限定",
                            "url": "https://itch.io/bundles",
                            "date": current_date
                        })

                        if len(bundles) >= 3:
                            break

                print(f"  Itch.ioから{len(bundles)}件のバンドルを取得")

            except ImportError:
                print("  beautifulsoup4がインストールされていません")

        except Exception as e:
            print(f"  Itch.io取得エラー: {e}")

        return bundles[:3]
    except Exception as e:
        print(f"  Itch.io情報の取得に失敗: {e}")
        return []

def fetch_reddit_bundles():
    """RedditからバンドルRSS情報を取得（APIの代わりにRSSフィードを使用）"""
    try:
        bundles = []
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Reddit RSS形式でデータを取得（JSONよりも安定）
        subreddits = [
            ('GameDeals', 'https://www.reddit.com/r/GameDeals/new/.rss'),
            ('humblebundles', 'https://www.reddit.com/r/humblebundles/new/.rss')
        ]

        if not feedparser:
            print("  feedparserがインストールされていないため、RedditのRSS取得をスキップ")
            # フォールバック: JSON APIを試行
            return fetch_reddit_bundles_json()

        for subreddit_name, rss_url in subreddits:
            try:
                print(f"  Reddit r/{subreddit_name} RSS取得中...")
                # feedparserを使用してRSSフィードを取得
                feed = feedparser.parse(rss_url)

                if not feed.entries:
                    print(f"  Reddit r/{subreddit_name}: 記事が見つかりませんでした")
                    continue

                for entry in feed.entries[:15]:
                    title = entry.get('title', '')
                    url_link = entry.get('link', '')
                    summary = entry.get('summary', '')  # RSSの要約フィールド
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
                        platform_url = 'https://www.humblebundle.com/'
                    elif 'fanatical' in title_lower:
                        platform = "Fanatical"
                        platform_url = 'https://www.fanatical.com/'
                    elif 'steam' in title_lower:
                        platform = "Steam"
                        platform_url = 'https://store.steampowered.com/'

                    if platform and platform_url:
                        # ゲーム無関係なコンテンツをフィルタリング
                        if not is_game_related_content(bundle_title, summary if summary else ""):
                            print(f"    ✗ 非ゲームバンドルを除外: {bundle_title[:40]}...")
                            continue

                        # RSSのsummaryから詳細情報とゲームタイトルを抽出
                        description = f"{platform}でお得なバンドルが登場！"
                        game_titles = []

                        if summary:
                            # Redditのメタ情報を削除
                            cleaned_text = clean_reddit_meta(summary)
                            cleaned_text = cleaned_text.replace('\n', ' ').replace('\r', ' ')

                            # ゲームタイトルを抽出（一般的なパターン）
                            # "Game1, Game2, Game3" や "- Game1 - Game2" などのパターンを検出
                            if len(cleaned_text) > 20:
                                # 翻訳して人間的な説明に（200文字程度に制限）
                                if translator:
                                    try:
                                        # 最初の300文字を翻訳
                                        text_to_translate = cleaned_text[:300] if len(cleaned_text) > 300 else cleaned_text
                                        translated_desc = translate_to_japanese(text_to_translate)
                                        # 200文字程度に制限
                                        if len(translated_desc) > 200:
                                            description = translated_desc[:200].rsplit('。', 1)[0] + '。'
                                        else:
                                            description = translated_desc
                                    except:
                                        description = f"{platform}でお得なバンドルが登場。複数のゲームがセットでお買い得。"
                                else:
                                    # 翻訳できない場合も200文字に制限
                                    if len(cleaned_text) > 200:
                                        description = cleaned_text[:200] + "..."
                                    else:
                                        description = cleaned_text
                            else:
                                # クリーンアップ後のテキストが短い場合、AIで生成
                                description = generate_description_with_ai(bundle_title, platform, "bundle")
                        else:
                            # summaryがない場合もAIで生成
                            description = generate_description_with_ai(bundle_title, platform, "bundle")

                        bundles.append({
                            "title": bundle_title,
                            "platform": platform,
                            "type": "bundle",
                            "description": description,
                            "price": "バンドル価格",
                            "originalPrice": "",
                            "discount": "",
                            "deadline": "期間限定",
                            "url": platform_url,
                            "date": current_date
                        })

                print(f"  Reddit r/{subreddit_name}: {len([b for b in bundles if b.get('date') == current_date])}件取得")

            except Exception as e:
                print(f"  Reddit r/{subreddit_name} RSS取得エラー: {e}")
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

def fetch_reddit_bundles_json():
    """RedditからバンドルJSON情報を取得（フォールバック用）"""
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
                        selftext = post_data.get('selftext', '')  # 投稿本文を取得
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
                            # ゲーム無関係なコンテンツをフィルタリング
                            if not is_game_related_content(bundle_title, selftext if selftext else ""):
                                print(f"    ✗ 非ゲームバンドルを除外: {bundle_title[:40]}...")
                                continue

                            # 投稿本文からゲーム名と詳細を抽出
                            description = f"{platform}でお得なバンドルが登場！"

                            if selftext:
                                # Redditのメタ情報を削除
                                cleaned_text = clean_reddit_meta(selftext)
                                cleaned_text = cleaned_text.replace('\n', ' ').replace('\r', ' ')

                                # 有効な説明文が残っている場合
                                if len(cleaned_text) > 20:
                                    # 英語の説明文を翻訳（200文字程度に制限）
                                    if translator:
                                        try:
                                            # 最初の300文字を翻訳
                                            text_to_translate = cleaned_text[:300] if len(cleaned_text) > 300 else cleaned_text
                                            translated_desc = translate_to_japanese(text_to_translate)
                                            # 200文字程度に制限
                                            if len(translated_desc) > 200:
                                                description = translated_desc[:200].rsplit('。', 1)[0] + '。'
                                            else:
                                                description = translated_desc
                                        except:
                                            description = generate_description_with_ai(bundle_title, platform, "bundle")
                                    else:
                                        # 翻訳できない場合も200文字に制限
                                        if len(cleaned_text) > 200:
                                            description = cleaned_text[:200] + "..."
                                        else:
                                            description = cleaned_text
                                else:
                                    # クリーンアップ後のテキストが短い場合、AIで生成
                                    description = generate_description_with_ai(bundle_title, platform, "bundle")
                            else:
                                # selftextがない場合もAIで生成
                                description = generate_description_with_ai(bundle_title, platform, "bundle")

                            bundles.append({
                                "title": bundle_title,
                                "platform": platform,
                                "type": "bundle",
                                "description": description,
                                "price": "バンドル価格",
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

def fetch_steam_sales():
    """Steamから特価セール情報を取得"""
    try:
        sales = []
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Steam特価情報（Steamストアのスペシャルページ）
        url = "https://store.steampowered.com/search/?specials=1&ndl=1"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')

                # Steamのセール情報を探す
                # 簡易的な実装（実際のSteam APIを使うとより正確）
                print(f"  Steam接続成功（セール情報は他ソースから取得）")

            except ImportError:
                print("  beautifulsoup4がインストールされていません")

        except Exception as e:
            print(f"  Steam取得エラー: {e}")

        return sales
    except Exception as e:
        print(f"  Steam情報の取得に失敗: {e}")
        return []

def fetch_isthereanydeal_sales():
    """IsThereAnyDealからセール情報を取得"""
    try:
        sales = []
        current_date = datetime.now().strftime("%Y-%m-%d")

        # IsThereAnyDealのトップセール
        url = "https://isthereanydeal.com/"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')

                # セール情報を探す
                # IsThereAnyDealは主にメタセール情報を提供
                print(f"  IsThereAnyDeal接続成功（セール情報は他ソースから取得）")

            except ImportError:
                print("  beautifulsoup4がインストールされていません")

        except Exception as e:
            print(f"  IsThereAnyDeal取得エラー: {e}")

        return sales
    except Exception as e:
        print(f"  IsThereAnyDeal情報の取得に失敗: {e}")
        return []

def fetch_gog_sales():
    """GOGからセール情報を取得"""
    try:
        sales = []
        current_date = datetime.now().strftime("%Y-%m-%d")

        # GOGのセールページ
        url = "https://www.gog.com/en/games?priceRange=0,15&discounted=true"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')

                # GOGのセール情報
                print(f"  GOG接続成功（セール情報は他ソースから取得）")

            except ImportError:
                print("  beautifulsoup4がインストールされていません")

        except Exception as e:
            print(f"  GOG取得エラー: {e}")

        return sales
    except Exception as e:
        print(f"  GOG情報の取得に失敗: {e}")
        return []

def fetch_reddit_sales():
    """RedditからセールRSS情報を取得（APIの代わりにRSSフィードを使用）"""
    try:
        sales = []
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Reddit RSS形式でデータを取得
        subreddits = [
            ('GameDeals', 'https://www.reddit.com/r/GameDeals/hot/.rss'),
            ('steamdeals', 'https://www.reddit.com/r/steamdeals/hot/.rss')
        ]

        if not feedparser:
            print("  feedparserがインストールされていないため、RedditのRSS取得をスキップ")
            # フォールバック: JSON APIを試行
            return fetch_reddit_sales_json()

        for subreddit_name, rss_url in subreddits:
            try:
                print(f"  Reddit r/{subreddit_name} RSS取得中...")
                feed = feedparser.parse(rss_url)

                if not feed.entries:
                    print(f"  Reddit r/{subreddit_name}: 記事が見つかりませんでした")
                    continue

                for entry in feed.entries[:15]:
                    title = entry.get('title', '')
                    url_link = entry.get('link', '')
                    summary = entry.get('summary', '')
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

                    if 'steam' in title_lower:
                        platform = "Steam"
                        platform_url = 'https://store.steampowered.com/'
                    elif 'epic' in title_lower:
                        platform = "Epic Games"
                        platform_url = 'https://store.epicgames.com/'
                    elif 'gog' in title_lower:
                        platform = "GOG"
                        platform_url = 'https://www.gog.com/'
                    elif 'fanatical' in title_lower:
                        platform = "Fanatical"
                        platform_url = 'https://www.fanatical.com/'
                    elif 'humble' in title_lower:
                        platform = "Humble Bundle"
                        platform_url = 'https://www.humblebundle.com/'

                    if platform and platform_url:
                        # タイトルを日本語化（英語の場合）
                        japanese_title = title
                        if translator and title:
                            # タイトルに英語が多く含まれる場合は翻訳
                            if any(c.isalpha() and ord(c) < 128 for c in title):
                                try:
                                    japanese_title = translate_to_japanese(title)
                                except:
                                    japanese_title = title

                        # RSSのsummaryから詳細情報を抽出（200文字程度に制限）
                        description = f"{platform}でお得なセールが開催中！"

                        if summary:
                            # Redditのメタ情報を削除
                            cleaned_text = clean_reddit_meta(summary)
                            cleaned_text = cleaned_text.replace('\n', ' ').replace('\r', ' ')

                            # 有効な説明文が残っている場合
                            if len(cleaned_text) > 20:
                                # 英語の説明文を翻訳（200文字程度に制限）
                                if translator:
                                    try:
                                        # 最初の300文字を翻訳
                                        text_to_translate = cleaned_text[:300] if len(cleaned_text) > 300 else cleaned_text
                                        translated_desc = translate_to_japanese(text_to_translate)
                                        # 200文字程度に制限
                                        if len(translated_desc) > 200:
                                            description = translated_desc[:200].rsplit('。', 1)[0] + '。'
                                        else:
                                            description = translated_desc
                                    except:
                                        description = f"{platform}でお得なセールが開催中。期間限定の特別価格。"
                                else:
                                    # 翻訳できない場合も200文字に制限
                                    if len(cleaned_text) > 200:
                                        description = cleaned_text[:200] + "..."
                                    else:
                                        description = cleaned_text
                            else:
                                # クリーンアップ後のテキストが短い場合、AIで生成
                                description = generate_description_with_ai(japanese_title, platform, "sale")
                        else:
                            # summaryがない場合もAIで生成
                            description = generate_description_with_ai(japanese_title, platform, "sale")

                        sales.append({
                            "title": japanese_title,
                            "platform": platform,
                            "type": "sale",
                            "description": description,
                            "price": "セール価格",
                            "originalPrice": "",
                            "discount": "",
                            "deadline": "期間限定",
                            "url": platform_url,
                            "date": current_date
                        })

                print(f"  Reddit r/{subreddit_name}: {len([s for s in sales if s.get('date') == current_date])}件取得")

            except Exception as e:
                print(f"  Reddit r/{subreddit_name} RSS取得エラー: {e}")
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

def fetch_reddit_sales_json():
    """RedditからセールJSON情報を取得（フォールバック用）"""
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
                        selftext = post_data.get('selftext', '')  # 投稿本文を取得
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
                            # タイトルを日本語化
                            japanese_title = title
                            if translator and title:
                                # タイトルに英語が多く含まれる場合は翻訳
                                if any(c.isalpha() and ord(c) < 128 for c in title):
                                    try:
                                        japanese_title = translate_to_japanese(title)
                                    except:
                                        japanese_title = title

                            # 投稿本文からセールの詳細を抽出（200文字程度に制限）
                            description = f"{platform}でお得なセールが開催中！"

                            if selftext:
                                # Redditのメタ情報を削除
                                cleaned_text = clean_reddit_meta(selftext)
                                cleaned_text = cleaned_text.replace('\n', ' ').replace('\r', ' ')

                                # 有効な説明文が残っている場合
                                if len(cleaned_text) > 20:
                                    # 英語の説明文を翻訳（200文字程度に制限）
                                    if translator:
                                        try:
                                            # 最初の300文字を翻訳
                                            text_to_translate = cleaned_text[:300] if len(cleaned_text) > 300 else cleaned_text
                                            translated_desc = translate_to_japanese(text_to_translate)
                                            # 200文字程度に制限
                                            if len(translated_desc) > 200:
                                                description = translated_desc[:200].rsplit('。', 1)[0] + '。'
                                            else:
                                                description = translated_desc
                                        except:
                                            description = generate_description_with_ai(japanese_title, platform, "sale")
                                    else:
                                        # 翻訳できない場合も200文字に制限
                                        if len(cleaned_text) > 200:
                                            description = cleaned_text[:200] + "..."
                                        else:
                                            description = cleaned_text
                                else:
                                    # クリーンアップ後のテキストが短い場合、AIで生成
                                    description = generate_description_with_ai(japanese_title, platform, "sale")
                            else:
                                # selftextがない場合もAIで生成
                                description = generate_description_with_ai(japanese_title, platform, "sale")

                            sales.append({
                                "title": japanese_title,
                                "platform": platform,
                                "type": "sale",
                                "description": description,
                                "price": "セール価格",
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

def is_game_related_content(title, description=""):
    """ゲーム関連のコンテンツかどうかを判定（非ゲームコンテンツを除外）"""
    title_lower = title.lower()
    desc_lower = description.lower()
    combined = f"{title_lower} {desc_lower}"

    # 除外するキーワード（本、映画、ツール、ハードウェアなど）
    exclude_keywords = [
        'book bundle', 'knit', 'knitting', '編み物', 'ニット',
        '予測ツール', 'prediction tool', 'tracker', 'calendar',
        'humble talk', 'podcast', 'video', 'movie', 'film',
        'running man', 'ランニングマン', '映画'
    ]

    # 除外キーワードが含まれている場合はFalse
    if any(keyword in combined for keyword in exclude_keywords):
        return False

    return True

def extract_game_title_from_review(title, summary=""):
    """レビュー記事のタイトルや要約からゲーム名を抽出"""
    # タイトルから【】や「」で囲まれたゲーム名を抽出
    import re

    # 日本語のパターン
    ja_patterns = [
        r'『([^』]+)』',  # 『ゲーム名』
        r'「([^」]+)」',  # 「ゲーム名」
        r'【([^】]+)】',  # 【ゲーム名】
    ]

    for pattern in ja_patterns:
        match = re.search(pattern, title)
        if match:
            return match.group(1)

    # 英語のパターン - タイトルの最初の部分（":" や "-" の前）
    if ':' in title:
        parts = title.split(':')
        game_name = parts[0].strip()
        # 一般的な記事のプレフィックスを除外
        if not any(prefix in game_name.lower() for prefix in ['review', 'preview', 'hands-on', 'first look']):
            return game_name

    return None

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
                            # ゲーム無関係なコンテンツをフィルタリング
                            if not is_game_related_content(title, summary_clean):
                                print(f"    ✗ 非ゲームコンテンツを除外: {title[:40]}...")
                                continue

                            # 英語記事は自動翻訳
                            if feed_info['lang'] == 'en':
                                # タイトルを翻訳
                                print(f"    翻訳中: {title[:40]}...")
                                translated_title = translate_to_japanese(title)

                                # ゲーム名を抽出
                                game_name = extract_game_title_from_review(translated_title, summary_clean)

                                # タイトルにゲーム名を【】で明示
                                if game_name:
                                    final_title = f"【{game_name}】{translated_title.replace(game_name, '').strip(' -:：')}"
                                else:
                                    final_title = translated_title

                                # 説明文を短縮（200-250文字程度）
                                if summary_clean and len(summary_clean) > 50:
                                    # 翻訳して短縮
                                    translated_summary = translate_to_japanese(summary_clean)
                                    # 200文字程度に制限
                                    if len(translated_summary) > 200:
                                        description = translated_summary[:200].rsplit('。', 1)[0] + '。'
                                    else:
                                        description = translated_summary
                                else:
                                    description = f"{feed_info['platform']}によるレビュー記事。ゲームプレイの感想や評価ポイントをチェック。"
                            else:
                                # 日本語記事の場合
                                # ゲーム名を抽出
                                game_name = extract_game_title_from_review(title, summary_clean)

                                # タイトルにゲーム名を【】で明示
                                if game_name and game_name not in title:
                                    final_title = f"【{game_name}】{title}"
                                else:
                                    final_title = title

                                # 説明文を短縮（200-250文字程度）
                                if summary_clean and len(summary_clean) > 50:
                                    # 200文字程度に制限
                                    if len(summary_clean) > 200:
                                        description = summary_clean[:200].rsplit('。', 1)[0] + '。'
                                    else:
                                        description = summary_clean
                                else:
                                    description = f"{feed_info['platform']}によるレビュー記事。実際にプレイした感想や評価をご覧いただけます。"

                            review_articles.append({
                                "title": final_title,
                                "platform": feed_info['platform'],
                                "type": "review",
                                "description": description,
                                "price": "",
                                "originalPrice": "",
                                "discount": "",
                                "deadline": "",
                                "url": link,
                                "date": current_date,
                                "is_translated": feed_info['lang'] == 'en'  # 翻訳済みフラグ
                            })

                            articles_from_this_feed += 1
                            print(f"    ✓ レビュー記事を発見: {final_title[:50]}...")

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
        print("  Reddit から取得中...")
        reddit_bundles = fetch_reddit_bundles()
        print("  Humble Bundle から取得中...")
        humble_bundles = fetch_humble_bundle_direct()
        print("  Fanatical から取得中...")
        fanatical_bundles = fetch_fanatical_bundles()
        print("  IndieGala から取得中...")
        indiegala_bundles = fetch_indiegala_bundles()
        print("  Itch.io から取得中...")
        itchio_bundles = fetch_itchio_bundles()

        # 全てのバンドル情報を統合
        all_bundles = reddit_bundles + humble_bundles + fanatical_bundles + indiegala_bundles + itchio_bundles

        # 重複を削除
        seen_titles = set()
        unique_bundles = []
        for bundle in all_bundles:
            title_key = bundle.get('title', '').lower()
            if title_key and title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_bundles.append(bundle)

        # reddit_bundlesを統合されたバンドルリストに変更
        reddit_bundles = unique_bundles

        print(f"\n  ✨ バンドル情報取得結果:")
        print(f"    - Reddit: {len(reddit_bundles) - len(humble_bundles) - len(fanatical_bundles) - len(indiegala_bundles) - len(itchio_bundles)}件")
        print(f"    - Humble Bundle: {len(humble_bundles)}件")
        print(f"    - Fanatical: {len(fanatical_bundles)}件")
        print(f"    - IndieGala: {len(indiegala_bundles)}件")
        print(f"    - Itch.io: {len(itchio_bundles)}件")
        print(f"    - 合計（重複除外後）: {len(reddit_bundles)}件")

        print("\n🔥 セール情報を取得中...")
        # 複数のソースからセール情報を取得
        print("  Reddit から取得中...")
        reddit_sales = fetch_reddit_sales()
        print("  Steam から取得中...")
        steam_sales = fetch_steam_sales()
        print("  IsThereAnyDeal から取得中...")
        itad_sales = fetch_isthereanydeal_sales()
        print("  GOG から取得中...")
        gog_sales = fetch_gog_sales()

        # 全てのセール情報を統合
        all_sales = reddit_sales + steam_sales + itad_sales + gog_sales

        # 重複を削除
        seen_titles = set()
        unique_sales = []
        for sale in all_sales:
            title_key = sale.get('title', '').lower()
            if title_key and title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_sales.append(sale)

        # reddit_salesを統合されたセールリストに変更
        reddit_sales = unique_sales

        print(f"\n  ✨ セール情報取得結果:")
        print(f"    - Reddit: {len(reddit_sales) - len(steam_sales) - len(itad_sales) - len(gog_sales)}件")
        print(f"    - Steam: {len(steam_sales)}件")
        print(f"    - IsThereAnyDeal: {len(itad_sales)}件")
        print(f"    - GOG: {len(gog_sales)}件")
        print(f"    - 合計（重複除外後）: {len(reddit_sales)}件")

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
            auto_platforms = ['Epic Games', 'Steam', 'GOG', 'Prime Gaming', 'Fanatical', 'Humble Bundle', 'IndieGala', 'Itch.io']
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

            # 自動取得された古いセール情報を削除（10日以上前）
            # セールは通常1-2週間続くため、やや長く保持する
            data['pc']['sale'] = clean_old_free_games(data['pc']['sale'], max_age_days=10)

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

            # 最新20件を保持（より多くのセール情報を表示）
            data['pc']['sale'] = unique_sales[:20]

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
