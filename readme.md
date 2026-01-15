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

## 🔗 参考サイト

- [JJ PCゲームラボ](https://jj-labo.seesaa.net/) - 本サイトの構成の参考元
- [IsThereAnyDeal](https://isthereanydeal.com/) - ゲーム価格比較
- [SteamDB](https://steamdb.info/) - Steam情報データベース

## 📝 更新方法

`index.html` を編集して、最新のセール情報や無料配布情報を追加してください。

更新例：
```html
<div class="deal-card">
    <div class="deal-header">
        <span class="platform-badge badge-steam">Steam</span>
        <span class="deal-type type-free">無料</span>
    </div>
    <div class="deal-title">ゲームタイトル</div>
    <div class="deal-description">ゲームの説明</div>
    <!-- ... -->
</div>
```

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。
