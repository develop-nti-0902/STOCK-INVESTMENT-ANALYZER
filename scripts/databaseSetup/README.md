---
title: Alembic 移行ドキュメント
last_updated: 2026-01-14
---

# 概要
このドキュメントは、既存の `scripts/databaseSetup` にある DB 初期化手順を Alembic に移行する際のローカル手順、マイグレーション作成方法、及びトラブルシューティングをまとめたものです。

# 前提
- Python 仮想環境が作成され、プロジェクト依存がインストールされていること（`poetry install` 等）
- プロジェクトルートに`.env`ファイルがあり、`DATABASE_URL`が設定されていること（例: `DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname`）。`env.py` が `.env` を読み込む実装になっていることを前提とします。
- `alembic` がプロジェクトに導入されていること（導入されていない場合は `poetry add --group dev alembic` を検討）

# ローカルでのマイグレーション適用手順
1. 仮想環境を有効化し、依存をインストールします。

```powershell
poetry install
poetry shell
```

2. `.env` ファイルを作成して `DATABASE_URL` を設定します（プロジェクトルートに配置）。例：

```text
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname
```

（`alembic/env.py` が `.env` を読み込む設定になっていれば、`poetry run alembic upgrade head` 等で `.env` の値が利用されます）

3. 初回または最新版へ適用するには：

```powershell
alembic upgrade head
```

4. ダウングレードしてクリーンアップする場合：

```powershell
alembic downgrade base
```

# マイグレーションファイルの作成方法

1. モデルの変更を行った後、自動生成を試みます：

```powershell
alembic revision --autogenerate -m "メッセージ"
```

2. 自動生成された差分を必ずレビューしてください。特に index, constraint, カスタム SQL（拡張や部分インデックスなど）は手動での修正が必要な場合があります。

3. 自動生成で対応できない操作（拡張モジュールの有効化、複雑なインデックス等）は `op.execute()` を使った手動記述を行ってください。

# 既存 SQL ファイルの扱い
- `scripts/databaseSetup/sql/` にある既存の SQL は移行の参考資料として保持してください。
- 初期マイグレーション作成時に既存 SQL と同等のスキーマが作成されることを確認し、必要ならばマイグレーション内に手動の `op.execute()` を追加して再現性を担保してください。

# トラブルシューティング
- `autogenerate` で差分が大きすぎる：モデルと既存スキーマの不一致があるため、差分を分割して手動でマイグレーションを作成してください。
- `alembic` 実行時にモデルが副作用を起こす（外部サービスに接続する等）：`env.py` 側で遅延インポート（モデルのインポートを関数内に移す）を検討してください。
- 非同期エンジンが必要：`alembic/env.py` を Alembic の Async クックブックに従って設定してください（`create_async_engine` を使用）。

# 参考
- Alembic ドキュメント: https://alembic.sqlalchemy.org/
- プロジェクト内 `alembic/` と `alembic.ini` を参照してください。

# 次のステップ（推奨）
- `alembic/env.py` を非同期エンジン + `target_metadata = Base.metadata` に対応させる
- 初期マイグレーションを作成し、`alembic/versions/` にコミットする
- CI ワークフローへ `alembic upgrade head` の検証ステップを追加する
