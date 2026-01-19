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
    """Redditのメタ情報を徹底的に削除"""
    if not text:
        return ""

    import html

    # HTMLエンティティをデコード（&#32; → 空白など）
    text = html.unescape(text)

    # HTMLタグを削除
    text = re.sub(r'<[^>]+>', '', text)

    # "submitted by /u/..." パターンを完全に削除（英語・日本語両方）
    text = re.sub(r'.*?submitted by.*?/u/\S+.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'/u/\S+\s*によって送信されました.*', '', text)
    text = re.sub(r'/u/\S+\s*により送信.*', '', text)
    text = re.sub(r'/u/\S+\s*が投稿.*', '', text)
    text = re.sub(r'送信者.*?/u/\S+.*', '', text)
    text = re.sub(r'投稿者.*?/u/\S+.*', '', text)
    text = re.sub(r'提供元.*?/u/\S+.*', '', text)

    # [link], [comments] などを削除（英語・日本語両方）
    text = re.sub(r'\[link\]|\[comments\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[リンク\]|\[コメント\]', '', text)

    # Redditユーザー名パターンを削除（単体でも）
    text = re.sub(r'u/\w+', '', text)
    text = re.sub(r'/u/\w+', '', text)

    # "このゲームの紹介は、...によって送信されました" のような文を削除
    text = re.sub(r'このゲームの紹介は、.*?によって.*?されました。?', '', text)
    text = re.sub(r'この.*?紹介.*?送信.*?', '', text)

    # "サイレント思考:" や "翻訳のポイント:" などAIの思考過程を削除
    text = re.sub(r'サイレント思考:.*', '', text, flags=re.DOTALL)
    text = re.sub(r'翻訳のポイント:.*', '', text, flags=re.DOTALL)
    text = re.sub(r'案\d+:.*', '', text, flags=re.DOTALL)
    text = re.sub(r'最終的な判断:.*', '', text, flags=re.DOTALL)
    text = re.sub(r'最終的な翻訳:.*', '', text, flags=re.DOTALL)

    # 価格表のような不自然な羅列を削除
    # "タイトル数 GBP USD EUR..." のようなパターン
    text = re.sub(r'タイトル数\s+GBP\s+USD\s+EUR.*', '', text)
    text = re.sub(r'Tier\s+GBP\s+USD\s+EUR.*', '', text)
    text = re.sub(r'£\s*[\d.]+\s+\$\s*[\d.]+.*?¥\s*[\d,]+.*', '', text)

    # 複数の空白・改行を1つに
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n+', ' ', text)

    return text.strip()

def humanize_text_with_ai(text, content_type="description"):
    """Groq APIを使って機械的な文章を自然な日本語にリライト"""
    if not groq_client or not text or len(text.strip()) < 10:
        return text

    try:
        # コンテンツタイプに応じたプロンプト
        if content_type == "title":
            prompt = f"""以下のゲーム記事タイトルを、自然で読みやすい日本語タイトルに整形してください。
- 不要な記号や価格情報は省略
- 簡潔で魅力的なタイトルに（50文字以内推奨）
- ゲーム名とプラットフォームの情報は保持

元のタイトル: {text}

IMPORTANT: 整形後のタイトル**のみ**を出力してください。説明・注釈・思考過程は一切不要です。"""

        elif content_type == "description":
            prompt = f"""以下のゲーム記事の説明文を、自然で読みやすい日本語に書き直してください。

要件：
- 機械翻訳のような不自然な表現を修正
- ゲーマーが読んで興味を持つような文章に
- 200〜400文字程度で、具体的で魅力的な説明に
- 事実は変えずに、表現を自然に
- 「です・ます」調で統一

元の説明文: {text}

IMPORTANT: 書き直した説明文**のみ**を出力してください。説明・注釈・思考過程・「サイレント思考」などは一切含めないでください。"""

        else:  # その他
            prompt = f"""以下のテキストを、自然で読みやすい日本語に書き直してください。
機械翻訳のような不自然な表現を修正し、人間が書いたような自然な文章にしてください。

元のテキスト: {text}

IMPORTANT: 書き直したテキスト**のみ**を出力してください。説明・注釈・思考過程は一切不要です。"""

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,  # 思考過程が出ないよう少し温度を下げる
            max_tokens=600    # より長い説明文に対応
        )

        result = response.choices[0].message.content.strip()

        # 思考過程が含まれていたら削除
        result = clean_reddit_meta(result)

        return result if result else text

    except Exception as e:
        print(f"  AI人間化エラー ({content_type}): {e}")
        return text  # エラー時は元のテキストを返す

def format_review_title(title):
    """レビュー記事のタイトルを【ゲーム名：レビュー】形式に整形"""
    if not title:
        return title

    # すでに【】形式の場合はそのまま返す
    if title.startswith('【') and '】' in title:
        return title

    # Groq APIでゲーム名を抽出して整形
    if groq_client:
        try:
            prompt = f"""以下のゲームレビュー記事タイトルから、ゲーム名を抽出して「【ゲーム名：レビュー】」の形式に整形してください。

要件：
- ゲーム名のみを抽出（不要な修飾語は削除）
- 必ず「【ゲーム名：レビュー】」の形式で出力
- ゲーム名は正式名称を使用
- 副題がある場合は含める

元のタイトル: {title}

IMPORTANT: 整形後のタイトル**のみ**を出力してください。説明は不要です。"""

            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,  # より正確な抽出のため温度を下げる
                max_tokens=100
            )

            result = response.choices[0].message.content.strip()

            # 結果が【】形式になっているか確認
            if result.startswith('【') and '】' in result:
                # ゲーム名が空でないことを確認（【：レビュー】のような形式を除外）
                game_name = result.split('：')[0].replace('【', '').strip()
                if game_name and len(game_name) > 0:
                    return result
                else:
                    # ゲーム名が空の場合は元のタイトルを使用
                    print(f"    ⚠ ゲーム名の抽出に失敗、元のタイトルを使用: {title[:40]}...")
                    return f"【{title}：レビュー】"
            else:
                # フォールバック：タイトルをそのまま【】で囲む
                return f"【{title}：レビュー】"

        except Exception as e:
            print(f"  レビュータイトル整形エラー: {e}")
            # エラー時はタイトルをそのまま【】で囲む
            return f"【{title}：レビュー】"
    else:
        # Groq APIがない場合は簡易整形
        # "〜のレビュー" "〜レビュー" などを削除してから整形
        cleaned = re.sub(r'(の)?レビュー|review', '', title, flags=re.IGNORECASE).strip()
        return f"【{cleaned}：レビュー】"

def simplify_title(title, max_length=80):
    """長すぎるタイトルを簡潔にする（ルールベース + AI）"""
    if not title:
        return title

    # 元のタイトルが短い場合はそのまま返す
    if len(title) <= max_length:
        return title

    # ルールベースでの簡潔化
    # [Reddit] [Platform] などのプレフィックスを削除
    cleaned_title = re.sub(r'^\[[\w\s]+\]\s*', '', title)

    # 価格情報の詳細を削除（例: "(2/4/7 for $4.99/$8.99/$13.99..." → ""）
    cleaned_title = re.sub(r'\(\d+/\d+/\d+\s+for\s+\$[\d\.\$/]+.*?\)', '', cleaned_title)
    cleaned_title = re.sub(r'\(Pay\s+\$[\d\s,\w]+\)', '', cleaned_title)

    # "choose from ..." 以降を削除
    cleaned_title = re.sub(r'\s+and\s+choose from\s+.*', '', cleaned_title, flags=re.IGNORECASE)

    # 複数の空白を1つに
    cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()

    # まだ長すぎる場合はAIで整形
    if len(cleaned_title) > max_length and groq_client:
        return humanize_text_with_ai(cleaned_title, content_type="title")
    else:
        return cleaned_title

def generate_description_with_ai(title, platform, deal_type="sale", original_text=""):
    """Groq APIを使ってタイトル（と元テキスト）から説明文を生成（失敗時はデフォルト説明文）"""
    if not groq_client:
        # Groq APIが利用できない場合はデフォルトの説明文
        if deal_type == "sale":
            return f"{platform}でお得なセールが開催中！期間限定の特別価格でゲームを手に入れるチャンス。"
        elif deal_type == "free":
            return f"{title}が{platform}で期間限定無料配布中！今すぐ入手して永久にライブラリに追加しよう。"
        else:
            return f"{platform}でお得なバンドルが登場！複数のゲームがセットでお買い得。"

    try:
        # deal_typeに応じたラベル
        type_label = {"sale": "セール", "bundle": "バンドル", "free": "無料配布"}.get(deal_type, "お得な情報")

        # Groq APIで説明文を生成
        if original_text and len(original_text) > 10:
            # 元テキストがある場合は、それを要約
            prompt = f"""以下のゲーム{type_label}情報から、魅力的な紹介文を日本語で生成してください。

要件：
- 200〜400文字程度の詳しい説明
- ゲーマーが読んで興味を持つような具体的な内容
- ゲームの特徴や魅力を自然な日本語で表現
- 「です・ます」調で統一
- 過度な宣伝文句は避け、事実ベースで

プラットフォーム: {platform}
タイトル: {title}
元の情報: {original_text[:800]}

紹介文のみを出力してください。"""
        else:
            # タイトルのみから生成
            prompt = f"""以下のゲーム{type_label}のタイトルから、魅力的な紹介文を日本語で生成してください。

要件：
- 200〜300文字程度の説明
- ゲーマーが興味を持つような内容
- ゲームの特徴を想像して自然な日本語で表現
- 「です・ます」調で統一
- タイトルから推測できる情報を基に

プラットフォーム: {platform}
タイトル: {title}

紹介文のみを出力してください。"""

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,  # より自然で多様な表現のため温度を上げる
            max_tokens=600    # より長い説明文に対応
        )

        description = response.choices[0].message.content.strip()
        if description:
            return description
        else:
            # フォールバック
            if deal_type == "sale":
                return f"{platform}でお得なセールが開催中！"
            elif deal_type == "free":
                return f"{title}が{platform}で期間限定無料配布中！"
            else:
                return f"{platform}でお得なバンドルが登場！"

    except Exception as e:
        print(f"  AI説明文生成エラー: {e}")
        if deal_type == "sale":
            return f"{platform}でお得なセールが開催中！期間限定の特別価格でゲームを手に入れるチャンス。"
        elif deal_type == "free":
            return f"{title}が{platform}で期間限定無料配布中！今すぐ入手して永久にライブラリに追加しよう。"
        else:
            return f"{platform}でお得なバンドルが登場！複数のゲームがセットでお買い得。"


def translate_to_japanese(text, max_retries=3, humanize=True):
    """Google翻訳で英語テキストを日本語に翻訳し、オプションで自然な日本語に整形"""
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

                # humanizeオプションがTrueの場合、Groq APIで自然な日本語に整形
                if humanize and len(translated_text) > 30:
                    humanized = humanize_text_with_ai(translated_text, content_type="description")
                    return humanized if humanized else translated_text
                else:
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

                        # 説明文の処理：英語の場合は翻訳して自然な日本語に
                        if description:
                            # 英語かどうかチェック
                            if any(c.isalpha() and ord(c) < 128 for c in description[:100]):
                                # 英語説明文を翻訳 + 人間化
                                description = translate_to_japanese(description, humanize=True)
                            elif len(description) < 100:
                                # 短すぎる場合はAIで充実化
                                description = generate_description_with_ai(
                                    title, "Epic Games", "free", description
                                )
                        else:
                            # 説明文がない場合はAIで生成
                            description = generate_description_with_ai(
                                title, "Epic Games", "free", ""
                            )

                        # 価格情報
                        original_price = "不明"
                        if game.get('price') and game['price'].get('totalPrice'):
                            price_info = game['price']['totalPrice']
                            original_price = f"¥{price_info.get('originalPrice', 0):,}"

                        free_games.append({
                            "title": f"{title} - Epic Games 無料配布中",
                            "platform": "Epic Games",
                            "type": "free",
                            "description": description,
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
                        # タイトルが有効で、バンドル関連で、かつ適切な長さであることを確認
                        if title and len(title) > 15 and 'bundle' in title.lower():
                            # 不完全なタイトル（"Bundle"や"Bundles"のみ）を除外
                            if title.lower() in ['bundle', 'bundles', 'バンドル']:
                                continue

                            # ゲームバンドルではないものを除外
                            exclude_keywords = ['book', 'knit', 'audio', 'music', 'software', 'font', 'asset', 'template', 'course', 'tutorial', 'ebook', 'audiobook']
                            if any(keyword in title.lower() for keyword in exclude_keywords):
                                continue

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

                    # ゲームバンドルではない記事を除外
                    exclude_keywords = [
                        'book', 'knit', 'question', 'how to', 'how long', 'tool', 'predictor',
                        'predict', 'when will', '本', 'ブック', 'どうやって', 'いつ', 'ツール',
                        'manga', 'comic', 'audio', 'music', 'software bundle', 'app bundle',
                        'font', 'asset', 'template', 'course', 'tutorial', 'ebook', 'audiobook'
                    ]

                    # タイトルと要約の両方をチェック
                    full_text_lower = f"{title_lower} {summary.lower() if summary else ''}"
                    is_excluded = any(keyword in full_text_lower for keyword in exclude_keywords)

                    if is_excluded:
                        print(f"    ✗ 除外: {title[:60]}...")
                        continue

                    # タイトルが短すぎる、または不完全な場合は除外
                    if len(title.strip()) < 10 or title.strip().lower() in ['bundle', 'bundles', 'バンドル']:
                        print(f"    ✗ 不完全なタイトルを除外: {title}")
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
                        # タイトルを簡潔にする
                        simplified_title = simplify_title(bundle_title, max_length=100)

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
                                # 長い説明文の場合、最初の800文字を使用（より詳しく）
                                if len(cleaned_text) > 800:
                                    cleaned_text = cleaned_text[:800] + "..."

                                # 翻訳して人間的な説明に（humanize=Trueで自然な日本語に整形）
                                if translator:
                                    try:
                                        translated_desc = translate_to_japanese(cleaned_text, humanize=True)
                                        description = f"{translated_desc}"
                                    except:
                                        description = f"{platform}でお得なバンドルが登場！複数のゲームがセットでお買い得。"
                                else:
                                    description = cleaned_text
                            else:
                                # クリーンアップ後のテキストが短い場合、AIで生成
                                description = generate_description_with_ai(simplified_title, platform, "bundle", cleaned_text)
                        else:
                            # summaryがない場合もAIで生成
                            description = generate_description_with_ai(simplified_title, platform, "bundle", "")

                        bundles.append({
                            "title": simplified_title,
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

        # 重複を削除（改善版：より厳密な正規化）
        seen_titles = set()
        unique_bundles = []
        for bundle in bundles:
            # タイトルを正規化（記号、空白、ゲーム名リストを削除して比較）
            title_key = bundle['title'].lower()
            # 記号と空白を統一
            title_key = re.sub(r'[^\w\s]', ' ', title_key)
            title_key = re.sub(r'\s+', ' ', title_key).strip()
            # ゲーム名のリスト部分を削除（"for the king"などの一般的なゲーム名を含む部分）
            # 主要な部分だけで重複判定（最初の5単語まで）
            title_key_short = ' '.join(title_key.split()[:5])

            if title_key_short not in seen_titles:
                seen_titles.add(title_key_short)
                unique_bundles.append(bundle)
            else:
                print(f"    ⚠ 重複を除外: {bundle['title'][:50]}...")

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

                        # ゲームバンドルではない記事を除外
                        exclude_keywords = [
                            'book', 'knit', 'question', 'how to', 'how long', 'tool', 'predictor',
                            'predict', 'when will', '本', 'ブック', 'どうやって', 'いつ', 'ツール',
                            'manga', 'comic', 'audio', 'music', 'software bundle', 'app bundle',
                            'font', 'asset', 'template', 'course', 'tutorial', 'ebook', 'audiobook'
                        ]

                        # タイトルと本文の両方をチェック
                        full_text_lower = f"{title_lower} {selftext.lower() if selftext else ''}"
                        is_excluded = any(keyword in full_text_lower for keyword in exclude_keywords)

                        if is_excluded:
                            print(f"    ✗ 除外: {title[:60]}...")
                            continue

                        # タイトルが短すぎる、または不完全な場合は除外
                        if len(title.strip()) < 10 or title.strip().lower() in ['bundle', 'bundles', 'バンドル']:
                            print(f"    ✗ 不完全なタイトルを除外: {title}")
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
                            # タイトルを簡潔にする
                            simplified_title = simplify_title(bundle_title, max_length=100)

                            # 投稿本文からゲーム名と詳細を抽出
                            description = f"{platform}でお得なバンドルが登場！"

                            if selftext:
                                # Redditのメタ情報を削除
                                cleaned_text = clean_reddit_meta(selftext)
                                cleaned_text = cleaned_text.replace('\n', ' ').replace('\r', ' ')

                                # 有効な説明文が残っている場合
                                if len(cleaned_text) > 20:
                                    # より長い説明文を取得（800文字まで）
                                    if len(cleaned_text) > 800:
                                        cleaned_text = cleaned_text[:800] + "..."

                                    # 英語の説明文を翻訳 + 人間化
                                    if translator:
                                        try:
                                            translated_desc = translate_to_japanese(cleaned_text, humanize=True)
                                            description = f"{translated_desc}"
                                        except:
                                            description = generate_description_with_ai(simplified_title, platform, "bundle", cleaned_text)
                                    else:
                                        description = cleaned_text
                                else:
                                    # クリーンアップ後のテキストが短い場合、AIで生成
                                    description = generate_description_with_ai(simplified_title, platform, "bundle", cleaned_text)
                            else:
                                # selftextがない場合もAIで生成
                                description = generate_description_with_ai(simplified_title, platform, "bundle", "")

                            bundles.append({
                                "title": simplified_title,
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

        # 重複を削除（改善版：より厳密な正規化）
        seen_titles = set()
        unique_bundles = []
        for bundle in bundles:
            # タイトルを正規化（記号、空白、ゲーム名リストを削除して比較）
            title_key = bundle['title'].lower()
            # 記号と空白を統一
            title_key = re.sub(r'[^\w\s]', ' ', title_key)
            title_key = re.sub(r'\s+', ' ', title_key).strip()
            # ゲーム名のリスト部分を削除（"for the king"などの一般的なゲーム名を含む部分）
            # 主要な部分だけで重複判定（最初の5単語まで）
            title_key_short = ' '.join(title_key.split()[:5])

            if title_key_short not in seen_titles:
                seen_titles.add(title_key_short)
                unique_bundles.append(bundle)
            else:
                print(f"    ⚠ 重複を除外: {bundle['title'][:50]}...")

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
                        # タイトルを日本語化（英語の場合）し、簡潔化
                        japanese_title = title
                        if translator and title:
                            # タイトルに英語が多く含まれる場合は翻訳
                            if any(c.isalpha() and ord(c) < 128 for c in title):
                                try:
                                    japanese_title = translate_to_japanese(title, humanize=False)
                                except:
                                    japanese_title = title

                        # タイトルを簡潔にする
                        simplified_title = simplify_title(japanese_title, max_length=100)

                        # RSSのsummaryから詳細情報を抽出
                        description = f"{platform}でお得なセールが開催中！"

                        if summary:
                            # Redditのメタ情報を削除
                            cleaned_text = clean_reddit_meta(summary)
                            cleaned_text = cleaned_text.replace('\n', ' ').replace('\r', ' ')

                            # 有効な説明文が残っている場合
                            if len(cleaned_text) > 20:
                                # より長い説明文を取得（800文字まで）
                                if len(cleaned_text) > 800:
                                    cleaned_text = cleaned_text[:800] + "..."

                                # 英語の説明文を翻訳 + 人間化
                                if translator:
                                    try:
                                        translated_desc = translate_to_japanese(cleaned_text, humanize=True)
                                        description = f"{translated_desc}"
                                    except:
                                        description = f"{platform}でお得なセールが開催中！期間限定の特別価格でゲームを手に入れるチャンス。"
                                else:
                                    description = cleaned_text
                            else:
                                # クリーンアップ後のテキストが短い場合、AIで生成
                                description = generate_description_with_ai(simplified_title, platform, "sale", cleaned_text)
                        else:
                            # summaryがない場合もAIで生成
                            description = generate_description_with_ai(simplified_title, platform, "sale", "")

                        sales.append({
                            "title": simplified_title,
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
                            # タイトルを日本語化し、簡潔化
                            japanese_title = title
                            if translator and title:
                                # タイトルに英語が多く含まれる場合は翻訳
                                if any(c.isalpha() and ord(c) < 128 for c in title):
                                    try:
                                        japanese_title = translate_to_japanese(title, humanize=False)
                                    except:
                                        japanese_title = title

                            # タイトルを簡潔にする
                            simplified_title = simplify_title(japanese_title, max_length=100)

                            # 投稿本文からセールの詳細を抽出
                            description = f"{platform}でお得なセールが開催中！"

                            if selftext:
                                # Redditのメタ情報を削除
                                cleaned_text = clean_reddit_meta(selftext)
                                cleaned_text = cleaned_text.replace('\n', ' ').replace('\r', ' ')

                                # 有効な説明文が残っている場合
                                if len(cleaned_text) > 20:
                                    # より長い説明文を取得（800文字まで）
                                    if len(cleaned_text) > 800:
                                        cleaned_text = cleaned_text[:800] + "..."

                                    # 英語の説明文を翻訳 + 人間化
                                    if translator:
                                        try:
                                            translated_desc = translate_to_japanese(cleaned_text, humanize=True)
                                            description = f"{translated_desc}"
                                        except:
                                            description = generate_description_with_ai(simplified_title, platform, "sale", cleaned_text)
                                    else:
                                        description = cleaned_text
                                else:
                                    # クリーンアップ後のテキストが短い場合、AIで生成
                                    description = generate_description_with_ai(simplified_title, platform, "sale", cleaned_text)
                            else:
                                # selftextがない場合もAIで生成
                                description = generate_description_with_ai(simplified_title, platform, "sale", "")

                            sales.append({
                                "title": simplified_title,
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
                                translated_title = translate_to_japanese(title, humanize=True)

                                # タイトルを【ゲーム名：レビュー】形式に整形
                                final_title = format_review_title(translated_title)

                                # 説明文を翻訳して充実化
                                if summary_clean and len(summary_clean) > 50:
                                    # より長い説明文を生成（人間化）
                                    translated_summary = translate_to_japanese(summary_clean, humanize=True)
                                    description = f"{translated_summary}"

                                    # 説明文が短すぎる場合は補足
                                    if len(description) < 100:
                                        description += f" {feed_info['platform']}による詳細なレビュー記事です。ゲームの魅力や特徴について深く掘り下げています。"
                                else:
                                    description = f"{final_title}について、{feed_info['platform']}が詳しくレビュー。ゲームプレイの感想や評価ポイントをチェックできます。"

                            else:
                                # 日本語記事も【ゲーム名：レビュー】形式に整形
                                final_title = format_review_title(title)

                                # 説明文を充実化
                                if summary_clean and len(summary_clean) > 50:
                                    # 日本語でも人間化処理を適用
                                    description = humanize_text_with_ai(summary_clean, content_type="description") if groq_client else summary_clean

                                    # 短い場合は補足
                                    if len(description) < 100:
                                        description += f" {feed_info['platform']}による詳細なレビュー記事。実際にプレイした感想や評価をご覧いただけます。"
                                else:
                                    description = f"{final_title}について、{feed_info['platform']}による実プレイレポートをお届けします。"

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

        # 重複を削除（改善版：より厳密な正規化）
        seen_titles = set()
        unique_bundles = []
        for bundle in all_bundles:
            title_key = bundle.get('title', '').lower()
            if not title_key:
                continue

            # 記号と空白を統一
            title_key = re.sub(r'[^\w\s]', ' ', title_key)
            title_key = re.sub(r'\s+', ' ', title_key).strip()
            # 主要な部分だけで重複判定（最初の5単語まで）
            title_key_short = ' '.join(title_key.split()[:5])

            if title_key_short not in seen_titles:
                seen_titles.add(title_key_short)
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

        # 重複を削除（改善版：より厳密な正規化）
        seen_titles = set()
        unique_sales = []
        for sale in all_sales:
            title_key = sale.get('title', '').lower()
            if not title_key:
                continue

            # 記号と空白を統一
            title_key = re.sub(r'[^\w\s]', ' ', title_key)
            title_key = re.sub(r'\s+', ' ', title_key).strip()
            # 主要な部分だけで重複判定（最初の6単語まで - セールタイトルは長めなので）
            title_key_short = ' '.join(title_key.split()[:6])

            if title_key_short not in seen_titles:
                seen_titles.add(title_key_short)
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

            # 保存前に説明文をクリーニング（Redditメタデータ削除）
            for game in all_new_games:
                if 'description' in game and game['description']:
                    game['description'] = clean_reddit_meta(game['description'])

            # 既存のゲームもクリーニング
            for game in data['pc']['free']:
                if 'description' in game and game['description']:
                    game['description'] = clean_reddit_meta(game['description'])

            data['pc']['free'] = all_new_games + data['pc']['free']

            # 重複を削除（タイトルベース・正規化強化）
            seen_titles = set()
            unique_games = []
            for game in data['pc']['free']:
                # タイトルを正規化（記号・空白を統一して比較）
                title_key = game.get('title', '').lower()
                title_key = re.sub(r'[^\w\s]', '', title_key)  # 記号削除
                title_key = re.sub(r'\s+', ' ', title_key).strip()  # 空白正規化

                if title_key not in seen_titles:
                    seen_titles.add(title_key)
                    unique_games.append(game)

            data['pc']['free'] = unique_games

        # レビュー記事を更新
        if review_articles:
            print(f"\n📚 {len(review_articles)}件のレビュー記事を取得しました")
            for article in review_articles:
                print(f"  - {article['title'][:50]}... ({article['platform']})")

                # 保存前に説明文をクリーニング（Redditメタデータ削除）
                if 'description' in article and article['description']:
                    article['description'] = clean_reddit_meta(article['description'])

            # reviewカテゴリが存在しない場合は作成
            if 'review' not in data['pc']:
                data['pc']['review'] = []

            # 既存のレビュー記事と新規記事をマージ（重複削除）
            # 手動で追加された記事（日付が1週間以上前のもの）は保持
            current_date = datetime.now()
            manual_reviews = []
            for review in data['pc']['review']:
                # 既存のレビューもクリーニング
                if 'description' in review and review['description']:
                    review['description'] = clean_reddit_meta(review['description'])

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

                # 保存前に説明文をクリーニング（Redditメタデータ削除）
                if 'description' in bundle and bundle['description']:
                    bundle['description'] = clean_reddit_meta(bundle['description'])

            # bundleカテゴリが存在しない場合は作成
            if 'bundle' not in data['pc']:
                data['pc']['bundle'] = []

            # 既存のバンドルもクリーニング
            for bundle in data['pc']['bundle']:
                if 'description' in bundle and bundle['description']:
                    bundle['description'] = clean_reddit_meta(bundle['description'])

            # 自動取得された古いバンドル情報を削除（14日以上前）
            # バンドルは通常2-4週間続くため、より長く保持する
            data['pc']['bundle'] = clean_old_free_games(data['pc']['bundle'], max_age_days=14)

            # 新しい情報を先頭に追加
            data['pc']['bundle'] = reddit_bundles + data['pc']['bundle']

            # 重複を削除（タイトルベース・正規化強化）
            seen_titles = set()
            unique_bundles = []
            for bundle in data['pc']['bundle']:
                # タイトルを正規化（記号・空白を統一して比較）
                title_key = bundle.get('title', '').lower()
                title_key = re.sub(r'[^\w\s]', ' ', title_key)  # 記号を空白に
                title_key = re.sub(r'\s+', ' ', title_key).strip()  # 空白正規化
                # 主要な部分だけで重複判定（最初の5単語まで）
                title_key_short = ' '.join(title_key.split()[:5])

                if title_key_short not in seen_titles:
                    seen_titles.add(title_key_short)
                    unique_bundles.append(bundle)

            # 最新15件を保持（より多くのバンドル情報を表示）
            data['pc']['bundle'] = unique_bundles[:15]

        # セール情報を更新
        if reddit_sales:
            print(f"\n🔥 {len(reddit_sales)}件のセール情報を取得しました")
            for sale in reddit_sales:
                print(f"  - {sale['title'][:50]}... ({sale['platform']})")

                # 保存前に説明文をクリーニング（Redditメタデータ削除）
                if 'description' in sale and sale['description']:
                    sale['description'] = clean_reddit_meta(sale['description'])

            # saleカテゴリが存在しない場合は作成
            if 'sale' not in data['pc']:
                data['pc']['sale'] = []

            # 既存のセールもクリーニング
            for sale in data['pc']['sale']:
                if 'description' in sale and sale['description']:
                    sale['description'] = clean_reddit_meta(sale['description'])

            # 自動取得された古いセール情報を削除（10日以上前）
            # セールは通常1-2週間続くため、やや長く保持する
            data['pc']['sale'] = clean_old_free_games(data['pc']['sale'], max_age_days=10)

            # 新しい情報を先頭に追加
            data['pc']['sale'] = reddit_sales + data['pc']['sale']

            # 重複を削除（タイトルベース・正規化強化）
            seen_titles = set()
            unique_sales = []
            for sale in data['pc']['sale']:
                # タイトルを正規化（記号・空白を統一して比較）
                title_key = sale.get('title', '').lower()
                title_key = re.sub(r'[^\w\s]', ' ', title_key)  # 記号を空白に
                title_key = re.sub(r'\s+', ' ', title_key).strip()  # 空白正規化
                # 主要な部分だけで重複判定（最初の6単語まで）
                title_key_short = ' '.join(title_key.split()[:6])

                if title_key_short not in seen_titles:
                    seen_titles.add(title_key_short)
                    unique_sales.append(sale)

            # 最新20件を保持（より多くのセール情報を表示）
            data['pc']['sale'] = unique_sales[:20]

        # 保存前に全カテゴリのデータをクリーニング（常に実行）
        print("\n🧹 全データのクリーニング中...")
        cleaned_count = 0

        # バンドルをクリーニング
        if 'bundle' in data.get('pc', {}):
            for item in data['pc']['bundle']:
                if 'description' in item and item['description']:
                    original = item['description']
                    item['description'] = clean_reddit_meta(item['description'])
                    if original != item['description']:
                        cleaned_count += 1

        # セールをクリーニング
        if 'sale' in data.get('pc', {}):
            for item in data['pc']['sale']:
                if 'description' in item and item['description']:
                    original = item['description']
                    item['description'] = clean_reddit_meta(item['description'])
                    if original != item['description']:
                        cleaned_count += 1

        # 無料ゲームをクリーニング
        if 'free' in data.get('pc', {}):
            for item in data['pc']['free']:
                if 'description' in item and item['description']:
                    original = item['description']
                    item['description'] = clean_reddit_meta(item['description'])
                    if original != item['description']:
                        cleaned_count += 1

        # レビューをクリーニング
        if 'review' in data.get('pc', {}):
            for item in data['pc']['review']:
                if 'description' in item and item['description']:
                    original = item['description']
                    item['description'] = clean_reddit_meta(item['description'])
                    if original != item['description']:
                        cleaned_count += 1

        if cleaned_count > 0:
            print(f"  ✨ {cleaned_count}件の説明文をクリーニングしました")
        else:
            print("  ✓ クリーニングが必要なデータはありませんでした")

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
