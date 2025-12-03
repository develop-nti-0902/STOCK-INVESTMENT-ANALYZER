category: setup
ai_context: low
last_updated: 2025-12-03
related_docs:
	- ../architecture/layers/data_storage_layer.md
	- ../README.md
	- ../develop-guide/development-workflow.md

# PostgreSQL セットアップ

## 目次
- [PostgreSQL セットアップ](#postgresql-セットアップ)
  - [目次](#目次)
  - [1. 概要](#1-概要)
  - [2. 対象ファイル・スクリプト](#2-対象ファイルスクリプト)
  - [3. `.env` の最小設定例](#3-env-の最小設定例)
  - [4. スクリプト実行例](#4-スクリプト実行例)
  - [5. 参考](#5-参考)
  - [6. 作成者情報](#6-作成者情報)

---

## 1. 概要

このドキュメントは、開発者が本プロジェクト用のローカル PostgreSQL を構成する際に必要な最小情報（参照するスクリプトと環境変数の例）を示します。詳細なインストール手順や検証手順は省略しています。

## 2. 対象ファイル・スクリプト

- スクリプトディレクトリ: `scripts/databaseSetup/`
  - `setup_db.bat`（Windows）
  - `setup_db.sh`（Linux/macOS）
- SQL スキーマ: `scripts/databaseSetup/sql/*.sql`（例: `create_stock_tables.sql`, `create_management_tables.sql`）

## 3. `.env` の最小設定例

プロジェクトルートに `.env` を置き、以下の最小設定を用意してください（機密情報は適切に管理してください）。

```env
PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGPASSWORD=<postgres_user_password>

NEW_DB=stock_investment_db
NEW_DB_USER=stock_user
NEW_DB_PASSWORD=<new_password>

DATABASE_URL=postgresql+asyncpg://stock_user:<new_password>@localhost:5432/stock_investment_db
```

`.env.example` に同様のテンプレートを追加してください（パスワードは空欄で）。

## 4. スクリプト実行例

- Windows (PowerShell):

```powershell
.
\scripts\databaseSetup\setup_db.bat
```

- Linux/macOS:

```bash
export $(cat .env | xargs)
bash scripts/databaseSetup/setup_db.sh
```

スクリプトは環境変数を参照して動作します。詳細な引数・オプションは各スクリプトのヘルプを参照してください。

## 5. 参考

- `scripts/databaseSetup/setup_db.bat`
- `scripts/databaseSetup/setup_db.sh`
- `scripts/databaseSetup/sql/create_stock_tables.sql`
- `docs/architecture/layers/data_storage_layer.md`

## 6. 作成者情報

作成者: 自動生成 / 編集調整
最終更新日: 2025-12-03

---
