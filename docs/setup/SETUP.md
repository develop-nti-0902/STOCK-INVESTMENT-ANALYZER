category: setup
ai_context: low
last_updated: 2025-12-07
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
  - [6. Alembic (マイグレーション) セットアップ](#6-alembic-マイグレーション-セットアップ)
    - [前提](#前提)
    - [環境変数（例）](#環境変数例)
    - [基本コマンド](#基本コマンド)
    - [非同期対応について](#非同期対応について)
    - [スクリプト](#スクリプト)
    - [CI での運用（簡易）](#ci-での運用簡易)
  - [7. 作成者情報](#7-作成者情報)

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


## 6. Alembic (マイグレーション) セットアップ

このセクションは、Alembic を用いたデータベーススキーマのバージョン管理と、ローカル/CI 環境での基本的な運用手順をまとめたものです。

### 前提

- Python 環境が整っていること（venv / conda 等）
- `alembic` がインストールされていること（例: `pip install alembic`）
- 環境変数 `DATABASE_URL` が設定されていること

### 環境変数（例）

- `DATABASE_URL` : SQLAlchemy の接続 URL
  - 例（PostgreSQL + asyncpg）: `postgresql+asyncpg://user:pass@localhost:5432/stock_db`

Windows PowerShell の例:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/stock_db"
```

UNIX の例:

```bash
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/stock_db"
```

### 基本コマンド

- 初期リビジョン作成（自動生成）:

```bash
alembic revision --autogenerate -m "Initial database schema"
```

- マイグレーション適用（最新版へ）:

```bash
alembic upgrade head
```

- マイグレーション履歴確認:

```bash
alembic history --verbose
```

- ダウングレード（特定リビジョン/ベースへ）:

```bash
alembic downgrade -1
alembic downgrade base
```

### 非同期対応について

本プロジェクトでは非同期ドライバを利用する場合があるため、`alembic/env.py` を非同期対応に設定してください。主なポイント:

- `AsyncEngine` を生成していること
- `run_migrations_online()` 内で非同期接続をラップしていること
- `target_metadata = Base.metadata` を正しくインポートしていること

既存の `alembic/env.py` を確認し、必要なら公式ドキュメントの非同期対応例に合わせて修正してください。

### スクリプト

- Windows: `scripts/databaseSetup/migrate.bat`
- Unix: `scripts/databaseSetup/migrate.sh`

これらは `alembic` の基本操作をラップするために利用できます。既存スクリプトがある場合は中身を確認し、必要に応じて `DATABASE_URL` の読み込みや仮想環境の有効化処理を追加してください。

### CI での運用（簡易）

- CI 環境に `DATABASE_URL` をシークレットで設定
- テスト用 DB を用意し、`alembic upgrade head` を実行してマイグレーションの成否を確認

## 7. 作成者情報

作成者: 自動生成 / 編集調整
最終更新日: 2025-12-07
```
