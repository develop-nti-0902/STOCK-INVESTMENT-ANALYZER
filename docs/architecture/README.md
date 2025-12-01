
# アーキテクチャドキュメント

## 目次
- [アーキテクチャドキュメント](#アーキテクチャドキュメント)
  - [目次](#目次)
  - [概要](#概要)
  - [ファイル構成](#ファイル構成)
    - [主要ファイル](#主要ファイル)
    - [レイヤ別ドキュメント (`layers/`)](#レイヤ別ドキュメント-layers)
  - [補足 / 運用](#補足--運用)

## 概要

- **目的**
	- このフォルダはシステムのアーキテクチャに関する設計資料を集約します。設計方針、レイヤ構成、各レイヤの役割や責務を確認するためのドキュメント群です。

- **利用方法**
	- 開発や設計レビュー時に参照してください。まず `architecture_overview.md` を読み、必要に応じて各レイヤの詳細に進んでください。

## ファイル構成

### 主要ファイル
- [architecture_overview.md](architecture_overview.md) — アーキテクチャ全体の概要と設計方針。
- [README.md](README.md) — この案内ファイル。

### レイヤ別ドキュメント (`layers/`)
以下はレイヤ別の詳細設計です。各ファイルは該当レイヤの目的、主要コンポーネント、責務、インターフェースを説明します。
- [layers/api_layer.md](layers/api_layer.md) — API 層の設計（外部/内部 API、エンドポイント方針など）。
- [layers/common_modules.md](layers/common_modules.md) — 共通モジュールやユーティリティのガイドライン。
- [layers/data_access_layer.md](layers/data_access_layer.md) — データアクセス層（リポジトリ、ORM、クエリ設計）。
- [layers/repository_di_usage.md](layers/repository_di_usage.md) — Repository依存性注入（DI）の使用例とパターン集。
- [layers/data_storage_layer.md](layers/data_storage_layer.md) — 永続化・ストレージ設計（DB、スキーマ方針、バックアップ）。
- [layers/presentation_layer.md](layers/presentation_layer.md) — プレゼンテーション層（フロントエンド/ビューに関する方針）。
- [layers/service_layer.md](layers/service_layer.md) — ビジネスロジック層（サービスの責務、トランザクション方針）。

## 補足 / 運用

- ドキュメントは随時更新してください。設計変更がある場合は変更箇所と理由を追記してください。
- より詳細な導入手順や CI/CD、ガイドラインは `docs/` の他ディレクトリ（`ci-cd/`、`guides/` など）を参照してください。

---
