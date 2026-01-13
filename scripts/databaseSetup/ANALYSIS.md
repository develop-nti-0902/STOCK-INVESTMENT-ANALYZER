# 既存スクリプト・スキーマ調査結果

このファイルは Issue #169（既存スクリプトとスキーマの調査・分析）の成果物です。

## 概要
- 調査対象: `scripts/databaseSetup/sql/` 配下のSQLおよび `setup_db.bat` / `setup_db.sh` の実行フロー
- 発見されたSQLファイル:
  - create_stock_tables.sql
  - create_management_tables.sql
  - create_user_tables.sql
  - drop_user_tables.sql

## テーブル依存関係と推奨作成順序（簡易）
1. `stock_master`（管理マスタ）
2. `stock_master_updates`
3. `batch_executions`
4. `batch_execution_details`（`batch_executions.id` にFK）
5. `users`
6. `user_transactions`（`users.id` にFK）
7. `user_portfolios`（`users.id` にFK）
8. `stocks_*` 系（`stock_master.stock_code` を参照するFKが存在するため `stock_master` の後）

備考: `stocks_*` は多数存在（1m,5m,15m,30m,1h,1d,1wk,1mo）。外部キーは `symbol` -> `stock_master(stock_code)`。

## PostgreSQL固有の考慮点
- シーケンス所有者やテーブル所有者を `db_user` 環境設定で変更している（`ALTER SEQUENCE ... OWNER TO` 等）。
- インデックス作成や大規模テーブル作成時は `CONCURRENTLY` 検討。

## 次の推奨作業（Issueフローに沿って）
1. Alembic 初期化（`alembic init`）と `alembic/env.py` の async 対応
2. モデルの `target_metadata = Base.metadata` を参照する設定
3. `--autogenerate` で初期リビジョン作成、差分が大きければ手動で調整
4. `scripts/databaseSetup` 内の `setup_db.*` を `alembic upgrade head` 呼び出しへ置換
5. CI ワークフローへマイグレーション適用テストを追加

## 受け入れ条件（次サブissue向け）
- SQL定義と上記作成順序がドキュメント化されていること
- PostgreSQL 固有の拡張・特殊処理箇所が列挙されていること

---
作業者: 自動生成レポート
日付: 2026-01-13
