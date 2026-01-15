# 🎮 ゲームお得情報キュレーション

PCゲーム・スマホゲームのお得情報をまとめたキュレーションサイトです。

## 📋 概要

このサイトは、以下のプラットフォームのゲームお得情報を提供します：

### PC向け
- **Steam** - デイリーディール、期間限定無料ゲーム
- **Epic Games** - 週替わり無料ゲーム、メガセール
- **GOG** - DRMフリーゲームの無料配布
- **Humble Bundle** - ゲームバンドル、Humble Choice
- **Fanatical** - Steamキーのバンドル＆セール

### スマホ向け
- **iOS (App Store)** - 期間限定無料アプリ、セール情報
- **Android (Google Play)** - 週末セール、無料化情報
- **Apple Arcade / Google Play Pass** - サブスクリプション情報
- **ゲーム内イベント** - 期間限定イベント、ログインボーナス

## ✨ 機能

- **タブ切り替え**: PC/スマホの情報を簡単に切り替え
- **カテゴリ分類**: 無料配布、セール、価格比較サイトなど
- **レスポンシブデザイン**: スマホでも快適に閲覧可能
- **外部リンク**: 各プラットフォームへ直接アクセス

## 🚀 GitHub Pagesでの公開方法

1. リポジトリの Settings → Pages へ移動
2. Source で `Deploy from a branch` を選択
3. Branch で `claude/game-deals-curation-AMQlx` (または `main`) を選択
4. フォルダは `/root` を選択
5. Save をクリック

数分後、以下のURLで公開されます：
```
https://WAYAWAYA-JP.github.io/Game/
```

## 🤖 自動更新機能

このサイトは毎日自動的に最新のゲーム情報を取得します。

### 自動取得される情報

1. **Epic Games 無料配布ゲーム**
   - 週替わり無料ゲーム
   - 期間限定無料配布

2. **Steam 無料配布ゲーム** (Reddit経由)
   - 期間限定無料配布
   - 週末無料プレイ
   - 100%オフセール

### 更新スケジュール

- **毎日** 日本時間の朝9時に自動実行
- GitHub Actionsで自動的に実行
- 変更があれば自動的にコミット・プッシュ

### 手動更新方法

GitHubリポジトリの「Actions」タブから手動実行も可能：
1. https://github.com/WAYAWAYA-JP/Game/actions
2. "Update Game Deals Daily" をクリック
3. "Run workflow" ボタンをクリック

### データソース

- Epic Games Store API
- Reddit (r/FreeGamesOnSteam, r/GameDeals)
- 今後追加予定: Steam API, GOG, Humble Bundle

## 🔗 参考サイト

- [JJ PCゲームラボ](https://jj-labo.seesaa.net/) - 本サイトの構成の参考元
- [IsThereAnyDeal](https://isthereanydeal.com/) - ゲーム価格比較
- [SteamDB](https://steamdb.info/) - Steam情報データベース

## 📝 記事の投稿方法

このサイトはJSONファイルでゲーム情報を管理しています。新しい記事を追加するには、`games-data.json` を編集してください。

### 記事の追加手順

1. `games-data.json` ファイルを開く
2. 追加したいカテゴリ（PC無料/PCセール/スマホ無料/スマホセール）を選択
3. 以下の形式で記事データを追加：

```json
{
  "title": "ゲームタイトル - プラットフォーム名",
  "platform": "Steam",
  "type": "free",
  "description": "ゲームの詳しい説明文。面白いポイントや特徴を書きましょう。",
  "price": "無料",
  "originalPrice": "¥2,000",
  "discount": "100% OFF",
  "deadline": "2026年1月20日まで",
  "url": "https://store.steampowered.com/...",
  "date": "2026-01-15"
}
```

### フィールドの説明

- **title**: 記事のタイトル（必須）
- **platform**: プラットフォーム名（Steam, Epic Games, GOG, Humble Bundle, Fanatical, iOS, Android, iOS/Android）
- **type**: "free"（無料）または "sale"（セール）
- **description**: ゲームの説明文（詳しく書くほど記事らしくなります）
- **price**: 現在の価格
- **originalPrice**: 元の価格（セールの場合）
- **discount**: 割引率
- **deadline**: 期限
- **url**: ゲームのURL（必須）
- **date**: 記事の投稿日

### 更新後の反映方法

1. `games-data.json` を保存
2. GitHubにプッシュ
3. GitHub Pagesが自動的に更新されます（数分かかる場合があります）

### 記事投稿の例

```json
{
  "title": "『Elden Ring』が史上最安値 - Steam ウィンターセール",
  "platform": "Steam",
  "type": "sale",
  "description": "フロム・ソフトウェアの大作オープンワールドアクションRPG「Elden Ring」が史上最安値！広大なフィールドを冒険し、強大なボスに挑む骨太のゲーム体験。2022年のGame of the Year受賞作が40%オフで入手可能です。",
  "price": "¥4,758",
  "originalPrice": "¥7,930",
  "discount": "40% OFF",
  "deadline": "2026年1月20日まで",
  "url": "https://store.steampowered.com/app/1245620/ELDEN_RING/",
  "date": "2026-01-10"
}
```

### ヒント

- **詳しい説明を書く**: JJPCゲームラボやAutomatonのように、ゲームの魅力や特徴を詳しく書くと記事らしくなります
- **期限を明記**: セール期限や無料配布期限を必ず記載しましょう
- **日付順に並べる**: 新しい記事ほど上に配置すると見やすくなります

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。
