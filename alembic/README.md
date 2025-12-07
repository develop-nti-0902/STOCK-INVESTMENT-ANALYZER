`alembic` ディレクトリ (STOCK-INVESTMENT-ANALYZER のマイグレーション)

使用上の注意:
- 実行時の DB 接続 URL はプロジェクトの `app.utils.database.get_database_url()` から取得します。
- 環境変数 `DATABASE_URL` は参照しません（基本設定が無い場合は `get_database_url()` を修正してください）。
- プロジェクトのタイムスタンプは UTC に対応しています。マイグレーション内での
  `server_default` やタイムスタンプ系の扱いは UTC 前提で実装してください。

よく使うコマンド (ローカル):

```powershell
# 現在のリビジョンを表示
alembic current

# 自動生成で新しいリビジョンを作成
alembic revision --autogenerate -m "initial"

# 最新までアップグレード
alembic upgrade head
```

Alembic 実行時は基本的に何も設定せず、そのまま実行してください。必要な接続情報は `get_database_url()` が返します。
