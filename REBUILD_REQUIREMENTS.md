# PCゲームキュレーションサイト 完全仕様書

## 📌 プロジェクト概要

PCゲームのお得情報（無料配布、バンドル、セール、レビュー記事）を自動収集・整理して提供するキュレーションサイト。GitHub Pagesで公開し、GitHub Actionsで毎日2回自動更新する。

---

## 🎯 主要機能

1. **自動データ収集**: 複数のゲーム情報ソースから自動取得
2. **AI翻訳・要約**: 英語記事を自動翻訳し、自然な日本語説明文を生成
3. **カテゴリ分類**: 無料/バンドル/セール/レビューの4カテゴリ
4. **レスポンシブUI**: PC/タブレット/スマホ対応
5. **自動更新**: 毎日朝9時・夜9時に自動実行（GitHub Actions）
6. **データクリーニング**: 重複排除、古いデータ削除、品質管理

---

## 🏗️ 技術スタック

### フロントエンド
- HTML5
- CSS3（Flexbox/Grid、グラデーション、アニメーション）
- Vanilla JavaScript（非同期処理）

### バックエンド（データ処理）
- Python 3.11
- **必須パッケージ** (`requirements.txt`):
  ```
  requests>=2.31.0
  feedparser>=6.0.10
  beautifulsoup4>=4.12.0
  deep-translator>=1.11.0
  groq>=0.4.0
  python-dotenv>=1.0.0
  ```

### インフラ
- **ホスティング**: GitHub Pages
- **CI/CD**: GitHub Actions
- **データ保存**: JSON（`games-data.json`）
- **バージョン管理**: Git

---

## 📁 ディレクトリ構造

```
/
├── .github/
│   └── workflows/
│       ├── update-games.yml       # 自動更新ワークフロー
│       └── deploy-pages.yml       # GitHub Pages デプロイ
├── scripts/
│   └── update-deals.py            # メイン更新スクリプト
├── .env.example                   # 環境変数テンプレート
├── .gitignore
├── requirements.txt               # Python依存パッケージ
├── README.md                      # プロジェクト説明
├── index.html                     # フロントエンド
└── games-data.json                # ゲーム情報データベース
```

---

## 🗂️ データ構造

### games-data.json スキーマ

```json
{
  "pc": {
    "free": [
      {
        "title": "ゲームタイトル",
        "platform": "Steam | Epic Games | GOG | 他",
        "type": "free",
        "description": "150-200文字の説明文",
        "price": "無料",
        "originalPrice": "¥2,000",
        "discount": "100% OFF",
        "deadline": "2026年1月20日まで",
        "url": "https://...",
        "date": "2026-01-23"
      }
    ],
    "bundle": [...],
    "sale": [...],
    "review": [
      {
        "title": "【ゲーム名：レビュー】",
        "platform": "AUTOMATON | PC Gamer | Rock Paper Shotgun | Polygon | doope! | インサイド",
        "type": "review",
        "description": "150-200文字の説明文",
        "price": "",
        "originalPrice": "",
        "discount": "",
        "deadline": "",
        "url": "https://...",
        "date": "2026-01-22",
        "is_translated": true
      }
    ]
  },
  "last_updated": "2026-01-23T02:01:09.409717"
}
```

---

## 📝 記事概要（description）の詳細仕様

### 基本ルール

| 項目 | 仕様 |
|------|------|
| **文字数** | **150〜200文字（厳守）** |
| **文体** | です・ます調で統一 |
| **改行** | なし（1段落） |
| **句読点** | 「、」「。」を適切に使用 |
| **完結性** | 必ず文末まで完結させる（途中で切らない） |

### カテゴリ別の必須要素

#### 1. 無料ゲーム（free）

**必須項目**:
- ✅ ゲームのジャンル（アクション、RPG、パズル等）
- ✅ ゲームの特徴・魅力（2-3点）
- ✅ 配布プラットフォーム
- ❌ 配布期間の詳細（deadlineフィールドに記載）

**例**:
```
中世を舞台にしたオープンワールドアクションゲームです。GTAスタイルの自由度の高いゲームプレイで、馬を盗んだり、衛兵と戦ったりできます。ユニークなクエストと豊富なポップカルチャー要素が魅力で、現在Epic Gamesで無料配布中です。
```

#### 2. バンドル（bundle）

**必須項目**:
- ✅ バンドル名
- ✅ 主要タイトル（2-3本）
- ✅ ジャンル
- ✅ 大まかな価格帯（例：$15〜）
- ❌ 「〜のバンドル。」のような簡素すぎる説明

**例**:
```
Just Causeシリーズの全作品を収録したバンドルです。オープンワールドアクションの人気シリーズで、Just Cause 4やDLC全てが含まれます。通常価格から大幅割引で、アクションゲーム好きには見逃せないお得なパックです。
```

#### 3. セール（sale）

**必須項目**:
- ✅ ゲームのジャンル・特徴
- ✅ 割引率または価格（具体的に）
- ✅ ゲームの評価・人気度（可能であれば）
- ❌ 冗長な繰り返し

**例**:
```
超常現象を扱うアクションアドベンチャーゲームで、美しいグラフィックと独特の世界観が高評価を得ています。Ultimate Editionには全DLCが含まれ、現在90%オフの$3.99という破格の価格で提供中です。
```

#### 4. レビュー記事（review）

**必須項目**:
- ✅ ゲームの評価ポイント
- ✅ レビューの内容概要（2-3点）
- ✅ 対象読者（どんな人におすすめか）
- ❌ 記事URLやメディア名の繰り返し
- ❌ 200文字で途切れないように完結させる

**例**:
```
タイムトラベルミステリーとブラックユーモアが融合した独特なアドベンチャーゲームです。PC Gamerのレビューでは、陰惨ながらもコメディ要素が魅力的だと評価されています。独創的な世界観を求めるプレイヤーにおすすめです。
```

### 禁止事項

❌ **含めてはいけない内容**:
- Redditのユーザー名（`/u/username`、`submitted by`等）
- HTMLタグ
- 同じ内容の繰り返し
- 不完全な文（途中で切れた文章）
- 「サイレント思考:」等のAI内部プロセス
- 価格表形式の羅列

---

## 🌐 データソース

### 無料ゲーム（free）

| ソース | 取得方法 | URL |
|--------|----------|-----|
| Epic Games Store | 公式API | `https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions` |
| Reddit - FreeGamesOnSteam | スクレイピング（HTML/JSON API） | `https://www.reddit.com/r/FreeGamesOnSteam/` |

### バンドル（bundle）

| ソース | 取得方法 | URL |
|--------|----------|-----|
| Humble Bundle | スクレイピング | `https://www.humblebundle.com/` |
| Fanatical | スクレイピング | `https://www.fanatical.com/` |
| IndieGala | スクレイピング | `https://www.indiegala.com/` |
| Itch.io | スクレイピング | `https://itch.io/bundles` |
| Reddit - GameDeals | スクレイピング（HTML/JSON API） | `https://www.reddit.com/r/GameDeals/` |

### セール（sale）

| ソース | 取得方法 | URL |
|--------|----------|-----|
| Steam | スクレイピング | `https://store.steampowered.com/` |
| GOG | スクレイピング | `https://www.gog.com/` |
| IsThereAnyDeal | API | `https://isthereanydeal.com/` |
| Reddit - GameDeals | スクレイピング（HTML/JSON API） | `https://www.reddit.com/r/GameDeals/` |

### レビュー記事（review）

| メディア | 言語 | RSS URL |
|----------|------|---------|
| AUTOMATON | 日本語 | `https://automaton-media.com/feed/` |
| doope! | 日本語 | `https://doope.jp/feed` |
| インサイド | 日本語 | `https://www.inside-games.jp/feeds/rss/` |
| PC Gamer | 英語 | `https://www.pcgamer.com/rss/` |
| Rock Paper Shotgun | 英語 | `https://www.rockpapershotgun.com/feed` |
| Polygon | 英語 | `https://www.polygon.com/rss/index.xml` |

---

## 🤖 自動更新の仕組み

### 更新スケジュール

- **頻度**: 毎日2回
  - 朝9時（日本時間）= UTC 0時
  - 夜9時（日本時間）= UTC 12時
- **トリガー**: GitHub Actions（Cron）
- **手動実行**: 可能（workflow_dispatch）

### 処理フロー

```
1. Python環境セットアップ（Python 3.11）
   ↓
2. 依存パッケージインストール
   ↓
3. update-deals.py 実行
   ├─ 無料ゲーム取得
   │  ├─ Epic Games API
   │  └─ Reddit スクレイピング
   ├─ バンドル取得
   │  ├─ Humble Bundle
   │  ├─ Fanatical
   │  ├─ IndieGala
   │  ├─ Itch.io
   │  └─ Reddit
   ├─ セール情報取得
   │  ├─ Steam
   │  ├─ IsThereAnyDeal
   │  ├─ GOG
   │  └─ Reddit
   └─ レビュー記事取得
      └─ RSSフィード → 翻訳
   ↓
4. データクリーニング
   ├─ 重複排除（タイトル正規化）
   ├─ 古いデータ削除（7-10日以上前）
   ├─ 説明文を150-200文字に調整
   └─ Redditメタデータ削除
   ↓
5. games-data.json 更新
   ↓
6. Git commit & push（リトライ機能付き）
   ↓
7. GitHub Pages 自動デプロイ
```

---

## 🔧 Python スクリプト仕様（update-deals.py）

### 主要関数

#### テキスト処理
- `clean_reddit_meta(text)` - Redditメタデータ削除
- `translate_to_japanese(text)` - Google翻訳（英→日）
- `humanize_text_with_ai(text)` - Groq APIで自然な日本語化（オプション）
- `generate_description_with_ai(game_data)` - 説明文生成
- `simplify_title(title)` - タイトル簡潔化
- `format_review_title(title)` - レビュータイトル整形（【ゲーム名：レビュー】形式）

#### データ取得
- `fetch_epic_free_games()` - Epic Games API
- `fetch_reddit_free_games()` - Reddit無料ゲーム
- `fetch_humble_bundle_direct()` - Humble Bundle
- `fetch_fanatical_bundles()` - Fanatical
- `fetch_indiegala_bundles()` - IndieGala
- `fetch_itchio_bundles()` - Itch.io
- `fetch_reddit_bundles()` - Redditバンドル
- `fetch_steam_sales()` - Steam
- `fetch_gog_sales()` - GOG
- `fetch_isthereanydeal_sales()` - IsThereAnyDeal
- `fetch_reddit_sales()` - Redditセール
- `fetch_review_articles()` - RSSレビュー記事

#### データ管理
- `clean_old_free_games(games_list, days=7)` - 古いデータ削除
- `remove_duplicates(games_list)` - 重複排除
- `update_games_data()` - メイン処理

### 重要な実装ポイント

#### 1. 説明文の長さ制限（150-200文字）
```python
def truncate_description(description, min_len=150, max_len=200):
    """説明文を150-200文字に調整（文の途中で切らない）"""
    if len(description) <= max_len:
        return description

    # max_len以内で最後の句点を探す
    truncated = description[:max_len]
    last_period = truncated.rfind('。')

    if last_period > min_len:
        return description[:last_period + 1]
    else:
        # 句点が見つからない場合はmax_lenで切って「…」を追加
        return description[:max_len - 1] + '…'
```

#### 2. 重複排除ロジック
```python
def normalize_title(title):
    """タイトルを正規化（最初の5-6単語、記号除去）"""
    # 記号・数字を除去
    cleaned = re.sub(r'[^\w\s]', '', title.lower())
    # 最初の5-6単語を取得
    words = cleaned.split()[:6]
    return ' '.join(words)

def remove_duplicates(games_list):
    """重複ゲームを削除"""
    seen = {}
    unique_games = []

    for game in games_list:
        norm_title = normalize_title(game['title'])
        if norm_title not in seen:
            seen[norm_title] = True
            unique_games.append(game)

    return unique_games
```

#### 3. エラーハンドリング（リトライ機能）
```python
import time
from functools import wraps

def retry_on_failure(max_retries=3, delay=2):
    """デコレータ: 失敗時にリトライ"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        print(f"❌ {func.__name__} failed after {max_retries} attempts: {e}")
                        return []
                    print(f"⚠️ Attempt {attempt + 1} failed, retrying in {delay}s...")
                    time.sleep(delay)
            return []
        return wrapper
    return decorator

@retry_on_failure(max_retries=3, delay=2)
def fetch_epic_free_games():
    # 実装...
```

#### 4. Redditメタデータ削除
```python
def clean_reddit_meta(text):
    """Redditメタデータを完全削除"""
    # パターンリスト
    patterns = [
        r'submitted by /u/\w+',
        r'\[link\]',
        r'\[comments\]',
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
        r'\d+ points?',
        r'\d+ comments?',
    ]

    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

    # 余分な空白削除
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned
```

---

## 🎨 フロントエンド仕様（index.html）

### レイアウト

```
┌─────────────────────────────────────┐
│         ヘッダー                    │
│   PCゲームお得情報キュレーション    │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│  [無料] [バンドル] [セール] [レビュー] │ ← タブ
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│  ┌───────────────────────────────┐  │
│  │ 📦 ゲームタイトル              │  │
│  │ 🏷️ Steam | Epic Games         │  │
│  │ 説明文（150-200文字）          │  │
│  │ 💰 ¥1,234 (元: ¥2,000)        │  │
│  │ ⏰ 2026年1月20日まで           │  │
│  │ [詳細を見る →]                │  │
│  └───────────────────────────────┘  │
│                                     │
│  ┌───────────────────────────────┐  │
│  │ ...                           │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

### 主要コンポーネント

#### 1. カテゴリタブ
```html
<div class="tabs">
  <button class="tab active" data-category="free">無料</button>
  <button class="tab" data-category="bundle">バンドル</button>
  <button class="tab" data-category="sale">セール</button>
  <button class="tab" data-category="review">レビュー</button>
</div>
```

#### 2. ゲームカード
```html
<div class="game-card" data-type="free">
  <div class="game-header">
    <h3 class="game-title">ゲームタイトル</h3>
    <span class="platform-badge">Epic Games</span>
  </div>
  <p class="game-description">説明文...</p>
  <div class="game-pricing">
    <span class="price">¥1,234</span>
    <span class="original-price">¥2,000</span>
    <span class="discount">40% OFF</span>
  </div>
  <div class="game-footer">
    <span class="deadline">⏰ 2026年1月20日まで</span>
    <a href="..." class="btn-details" target="_blank">詳細を見る →</a>
  </div>
</div>
```

#### 3. JavaScript（データ読み込み）
```javascript
let gamesData = {};

async function loadGamesData() {
  try {
    const response = await fetch('games-data.json');
    gamesData = await response.json();
    displayGames('free');
  } catch (error) {
    console.error('データ読み込みエラー:', error);
  }
}

function displayGames(category) {
  const container = document.getElementById('games-container');
  const games = gamesData.pc[category] || [];

  container.innerHTML = games.map(game => createGameCard(game)).join('');
}

function createGameCard(game) {
  return `
    <div class="game-card">
      <div class="game-header">
        <h3>${game.title}</h3>
        <span class="platform-badge">${game.platform}</span>
      </div>
      <p class="game-description">${game.description}</p>
      ${createPricing(game)}
      <div class="game-footer">
        ${game.deadline ? `<span class="deadline">⏰ ${game.deadline}</span>` : ''}
        <a href="${game.url}" class="btn-details" target="_blank">詳細を見る →</a>
      </div>
    </div>
  `;
}

// タブ切り替え
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', (e) => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    e.target.classList.add('active');
    displayGames(e.target.dataset.category);
  });
});

// 初期化
loadGamesData();
```

### CSS スタイリング

#### レスポンシブブレークポイント
```css
/* モバイル: 〜768px */
@media (max-width: 768px) {
  .game-card { width: 100%; }
}

/* タブレット: 769px〜1024px */
@media (min-width: 769px) and (max-width: 1024px) {
  .game-card { width: 48%; }
}

/* デスクトップ: 1025px〜 */
@media (min-width: 1025px) {
  .game-card { width: 32%; }
}
```

#### プラットフォームバッジの色分け
```css
.platform-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.85em;
  font-weight: bold;
}

.platform-badge[data-platform="Steam"] { background: #1b2838; color: #fff; }
.platform-badge[data-platform="Epic Games"] { background: #313131; color: #fff; }
.platform-badge[data-platform="GOG"] { background: #86328a; color: #fff; }
.platform-badge[data-platform="Humble Bundle"] { background: #cc2929; color: #fff; }
```

---

## ⚙️ GitHub Actions 設定

### 1. 自動更新ワークフロー（.github/workflows/update-games.yml）

```yaml
name: Update Game Deals

on:
  schedule:
    # 毎日朝9時（日本時間）= UTC 0時
    - cron: '0 0 * * *'
    # 毎日夜9時（日本時間）= UTC 12時
    - cron: '0 12 * * *'
  workflow_dispatch:  # 手動実行

permissions:
  contents: write

jobs:
  update:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run update script
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
        run: |
          python scripts/update-deals.py

      - name: Commit and push
        run: |
          git config --local user.name "github-actions[bot]"
          git config --local user.email "github-actions[bot]@users.noreply.github.com"

          # 変更があるかチェック
          if git diff --quiet games-data.json; then
            echo "No changes to commit"
            exit 0
          fi

          git add games-data.json
          git commit -m "🎮 自動更新: 無料/バンドル/セール/レビュー記事を更新 ($(date +'%Y-%m-%d'))"

          # リトライロジック（最大5回）
          for i in {1..5}; do
            if git push; then
              echo "Push successful"
              exit 0
            fi
            echo "Push failed, retrying in 5s... (attempt $i/5)"
            sleep 5
            git pull --rebase origin ${{ github.ref_name }}
          done

          echo "Push failed after 5 attempts"
          exit 1
```

### 2. GitHub Pages デプロイ（.github/workflows/deploy-pages.yml）

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Pages
        uses: actions/configure-pages@v4

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: '.'

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

---

## 🔑 環境変数（.env.example）

```bash
# Groq API（オプション：記事説明文の生成に使用）
# https://console.groq.com/keys で無料取得可能
# 未設定の場合はデフォルトの説明文を使用
GROQ_API_KEY=your_groq_api_key_here
```

### GitHub Secrets 設定

1. GitHubリポジトリ → Settings → Secrets and variables → Actions
2. `New repository secret` をクリック
3. Name: `GROQ_API_KEY`
4. Value: Groq APIキー
5. `Add secret` をクリック

---

## 📦 requirements.txt

```
requests>=2.31.0
feedparser>=6.0.10
beautifulsoup4>=4.12.0
deep-translator>=1.11.0
groq>=0.4.0
python-dotenv>=1.0.0
```

---

## 🚀 実装の順序

### Phase 1: 基本セットアップ
1. ✅ ディレクトリ構造作成
2. ✅ `requirements.txt` 作成
3. ✅ `.gitignore` 作成
4. ✅ `.env.example` 作成
5. ✅ `README.md` 作成

### Phase 2: データ取得スクリプト
1. ✅ `scripts/update-deals.py` 作成
2. ✅ Epic Games API 実装
3. ✅ Reddit スクレイピング実装
4. ✅ バンドルサイト スクレイピング実装
5. ✅ セール情報取得実装
6. ✅ RSSレビュー記事取得実装
7. ✅ 翻訳・AI要約機能実装
8. ✅ データクリーニング実装

### Phase 3: フロントエンド
1. ✅ `index.html` 基本構造
2. ✅ CSS スタイリング
3. ✅ JavaScript データ読み込み
4. ✅ タブ切り替え機能
5. ✅ レスポンシブ対応

### Phase 4: 自動化
1. ✅ GitHub Actions ワークフロー作成
2. ✅ GitHub Pages 設定
3. ✅ 環境変数設定
4. ✅ テスト実行

---

## 🧪 テスト項目

### スクリプトテスト
- [ ] Epic Games API からデータ取得
- [ ] Reddit から無料ゲーム取得
- [ ] バンドル情報取得（Humble、Fanatical等）
- [ ] セール情報取得
- [ ] RSSレビュー記事取得
- [ ] 翻訳機能（英→日）
- [ ] 説明文が150-200文字に収まる
- [ ] 重複削除機能
- [ ] 古いデータ削除（7日以上前）
- [ ] JSON形式の正しさ

### フロントエンドテスト
- [ ] データ読み込み成功
- [ ] タブ切り替え動作
- [ ] ゲームカード表示
- [ ] レスポンシブ表示（PC/タブレット/スマホ）
- [ ] リンクが正しく動作

### GitHub Actions テスト
- [ ] 手動実行が成功
- [ ] スケジュール実行が成功
- [ ] コミット・プッシュが成功
- [ ] GitHub Pages デプロイが成功

---

## 📌 注意事項

### スクレイピング
- **User-Agent設定**: 必ずUser-Agentヘッダーを設定
- **リクエスト間隔**: 過度なリクエストを避ける（1-2秒間隔）
- **エラーハンドリング**: ネットワークエラー、タイムアウトに対応
- **リトライ機能**: 失敗時は3回までリトライ

### データ品質
- **説明文の長さ**: 必ず150-200文字に収める
- **重複排除**: タイトル正規化で確実に重複削除
- **古いデータ**: 7-10日以上前のデータは削除
- **メタデータ削除**: Redditのユーザー名等は完全削除

### GitHub Actions
- **APIレート制限**: GitHub Actionsの実行回数制限に注意
- **シークレット管理**: APIキーはGitHub Secretsで管理
- **プッシュ失敗**: リトライ機能で対応（最大5回）

---

## 🆘 トラブルシューティング

### よくある問題

#### 1. スクレイピングが失敗する
- **原因**: サイト構造変更、ネットワークエラー
- **対処**: User-Agent設定、リトライ機能、タイムアウト延長

#### 2. 説明文が途中で切れる
- **原因**: 200文字で強制カット
- **対処**: `truncate_description()` で句点位置を検索して切る

#### 3. 重複データが残る
- **原因**: タイトル正規化が不十分
- **対処**: `normalize_title()` の改善（記号除去、単語数調整）

#### 4. GitHub Actions プッシュ失敗
- **原因**: 同時実行によるコンフリクト
- **対処**: リトライロジックで `git pull --rebase` 実行

#### 5. 翻訳が不自然
- **原因**: Google翻訳の限界
- **対処**: Groq API（Llama 3.3-70b）で自然な日本語化

---

## 📚 参考資料

### API ドキュメント
- [Epic Games Store API](https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions)
- [Groq API](https://console.groq.com/docs)
- [GitHub Actions](https://docs.github.com/en/actions)
- [GitHub Pages](https://docs.github.com/en/pages)

### Python ライブラリ
- [requests](https://requests.readthedocs.io/)
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [feedparser](https://feedparser.readthedocs.io/)
- [deep-translator](https://deep-translator.readthedocs.io/)

---

## ✅ チェックリスト

実装完了時に以下を確認：

### セットアップ
- [ ] リポジトリ作成
- [ ] ディレクトリ構造完成
- [ ] 依存パッケージインストール
- [ ] 環境変数設定

### スクリプト
- [ ] update-deals.py 動作確認
- [ ] 全データソースから取得成功
- [ ] 説明文が150-200文字
- [ ] 重複排除動作
- [ ] 古いデータ削除動作

### フロントエンド
- [ ] index.html 表示確認
- [ ] タブ切り替え動作
- [ ] レスポンシブ表示
- [ ] デザイン完成

### 自動化
- [ ] GitHub Actions 設定完了
- [ ] 手動実行成功
- [ ] スケジュール実行確認
- [ ] GitHub Pages デプロイ成功

### 品質
- [ ] 説明文の品質確認
- [ ] リンク動作確認
- [ ] エラーハンドリング確認
- [ ] パフォーマンス確認

---

## 🎯 成果物

完成時に以下が揃っていること：

1. ✅ **動作する静的サイト**（GitHub Pages）
2. ✅ **自動更新スクリプト**（毎日2回実行）
3. ✅ **高品質な記事概要**（150-200文字、カテゴリ別フォーマット）
4. ✅ **レスポンシブUI**（PC/タブレット/スマホ対応）
5. ✅ **完全なドキュメント**（README.md）

---

## 🔄 今後の拡張案（オプション）

- [ ] 検索機能追加
- [ ] フィルタリング機能（プラットフォーム別、価格帯別）
- [ ] ソート機能（日付順、割引率順）
- [ ] お気に入り機能（LocalStorage）
- [ ] メール通知機能
- [ ] Discordボット連携
- [ ] API提供（games-data.json を公開API化）

---

**以上で完全仕様書は終了です。この仕様書を元に一から実装してください。**
