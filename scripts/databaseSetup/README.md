---
title: Database setup helper scripts
last_updated: 2026-03-12
---

# 概要
このファイルは `scripts/databaseSetup` 配下にあるスクリプトの使い方・振る舞い・注意点を一からまとめたものです。

目的:
- ローカル開発環境で SQLite データベースを素早く準備・削除し、Alembic マイグレーションとモデルの同期を支援する。
- 以前はプラットフォームごとに異なるシェル/BAT スクリプトがありましたが、現在はクロスプラットフォームな Python スクリプトに統合しています。

対象読者:
- ローカルで開発・テストを行う開発者
- CI のジョブを設定する運用担当者

---

## 目次
- スクリプト一覧
- 動作の優先順位・環境変数
- 使い方（実行例）
- オプション一覧
- 実行フロー（内部処理の要点）
- トラブルシューティング
- CI / 運用時の注意
- 変更履歴

---

## スクリプト一覧

現在の実装（2026-03-12）:

- `setup_sqlite.py` — SQLite DB の作成・初期化、Alembic マイグレーションの適用、`ensure_sqlite_tables.py` による `create_all` のフォールバックまで行う統合スクリプト。
	- Windows では既定で `DATABASE_URL` を `setx` によりユーザ環境変数へ永続化する（副作用が望ましくない場合は `--no-persist` を使用して無効化可能）。

- `teardown_sqlite.py` — 指定された SQLite DB ファイルを削除するスクリプト。ダウングレードは行わず、ファイル削除でクリーンアップする想定。

- `ensure_sqlite_tables.py` — SQLAlchemy の `Base.metadata` を参照し、DB に不足しているテーブルがあれば `create_all()` で作成する補助スクリプト。単体でも動作する。

（古いラッパー `setup_sqlite.bat` / `setup_sqlite.sh` / `teardown_sqlite.bat` は削除され、Python 実装に置き換え済み）

---

## 動作の優先順位・環境変数

どのスクリプトも DB の指定優先度は以下のとおりです。

1. コマンドライン引数（例: `python setup_sqlite.py F:\path\to\db.db`）
2. 環境変数 `SQLITE_DB_FILE`（`.env` 経由で読み込まれる）
3. 環境変数 `DATABASE_URL`（`.env` 経由）
4. デフォルト: `<repo_root>/data/sqlite.db`

注意: `DATABASE_URL` に `sqlite:///...` の形式が入っている場合、ファイルパスを適切に扱うため正規化されます。

---

## 使い方（実行例）

推奨は `poetry run` 経由で実行することです（プロジェクトの仮想環境を使うため）。

基本（デフォルト DB を使用）:

```powershell
poetry run python scripts/databaseSetup/setup_sqlite.py
```

明示的に DB ファイルを指定する場合:

```powershell
poetry run python scripts/databaseSetup/setup_sqlite.py F:\my\path\stock.db
```

Windows で永続化を行いたくない場合（`setx` を使いたくないとき）:

```powershell
poetry run python scripts/databaseSetup/setup_sqlite.py --no-persist
```

DB を削除する（teardown）:

```powershell
poetry run python scripts/databaseSetup/teardown_sqlite.py
```

または特定ファイルを削除:

```powershell
poetry run python scripts/databaseSetup/teardown_sqlite.py F:\my\path\stock.db
```

※ Unix 系でも同様に `poetry run python ...` を利用してください。

---

## オプション一覧

- `--no-persist` (setup_sqlite.py): Windows の既定動作である `setx` による `DATABASE_URL` の永続化を抑止します。CI や共有環境では必ず付けて実行することを推奨します。

（将来的に `--force` や `--backup` 等のフラグを追加することも検討できます）

---

## 実行フロー（内部処理の要点）

setup_sqlite.py の主な処理:

1. `.env` が存在すれば読み込み（既に環境変数にセットされている値は上書きしない）
2. 優先順位に従って DB 値を決定（CLI > SQLITE_DB_FILE > DATABASE_URL > default）
3. DB ファイルが存在しなければ作成（`sqlite3` バイナリがあればそれを優先的に使用、無ければ Python の sqlite3 で作成）
4. `DATABASE_URL` を SQLAlchemy 用の `sqlite:///abs/path` 形式に正規化し、環境変数に設定。Windows では既定で `setx` により永続化する（`--no-persist` で抑止）
5. Alembic を呼び出して `upgrade heads` を実行
6. `ensure_sqlite_tables.py` を呼び出し、`Base.metadata` に基づくテーブル作成（必要な場合）

teardown_sqlite.py の主な処理:

1. `.env` 読み込み、DB 値の決定（setup と同じ優先順位）
2. Alembic の存在確認（未インストールならエラー）
3. 指定の DB ファイルを削除（読み取り専用フラグの解除等を試みる）

---

## トラブルシューティング

- Alembic が見つからないエラー: `poetry add --group dev alembic` で開発依存に入れるか、使用している Python に Alembic をインストールしてください（CI ではイメージに含めるかジョブで pip install する）。
- DB ファイルが作れない/開けない: ディレクトリのパーミッション、アンチウィルスやロック状態を確認してください。Windows ではパスに日本語/特殊文字があると問題になる場合があります。
- `ensure_sqlite_tables.py` 実行後もテーブル不足が残る: `Base.metadata` の対象が正しいか、モデルが正しく読み込まれているかを確認してください。特に `app.models` の import 側で副作用がないか注意。

---

## CI / 運用時の注意

- CI では `--no-persist` を必ず付ける（`setx` による環境変数の恒久化を防ぐため）。
- 共有環境や本番での DB 削除は危険操作です。`teardown_sqlite.py` を自動で実行するジョブは作らないでください。HITL（人の承認）を必須にしてください。
- `DATABASE_URL` を CI 環境変数として直接設定することを推奨します（スクリプトに永続化させない）。

---

## テスト手順（簡易）

ローカルでの素早い検証手順:

1. 仮想環境を有効化し依存をインストール

```powershell
poetry install
```

2. DB を作成してマイグレーションを適用

```powershell
poetry run python scripts/databaseSetup/setup_sqlite.py
```

3. 問題なければ DB を削除

```powershell
poetry run python scripts/databaseSetup/teardown_sqlite.py
```

---

## 変更履歴

- 2026-03-12: スクリプトを Python 化し `setup_sqlite.py` / `teardown_sqlite.py` を追加。既存の `.bat` / `.sh` は削除。

---

必要であれば、CI 用の具体的な job スニペット（GitHub Actions, Azure Pipelines など）や、`poetry` 以外の実行例を追記します。

# scripts/databaseSetup にあるスクリプト（概要と使い方）

このディレクトリにはローカル開発時に SQLite を準備・削除するための補助スクリプトがあります。
2026-03-12 時点で Windows/.sh のラッパーは廃止され、以下の Python スクリプトに統合されています。

- **setup_sqlite.py** — SQLite DB の準備および Alembic マイグレーション実行、テーブル不足時の `create_all` を行います。
	- 優先順位: CLI 引数 > `SQLITE_DB_FILE` (.env) > `DATABASE_URL` (.env) > `repo/data/sqlite.db`
	- Windows では既定で `DATABASE_URL` をユーザ環境変数へ `setx` で永続化します（必要なければ `--no-persist` を付けて無効化してください）。
	- 使い方例:

```powershell
poetry run python scripts/databaseSetup/setup_sqlite.py
# または明示的に DB を指定
poetry run python scripts/databaseSetup/setup_sqlite.py F:\path\to\mydb.db
```

	- 内部では Alembic を呼び出し、続けて `ensure_sqlite_tables.py` を実行してメタデータからテーブル作成を行います。

- **teardown_sqlite.py** — 指定された SQLite DB ファイルを削除します（ダウングレードは行わずファイル削除でクリーンアップします）。
	- 優先順位は `setup_sqlite.py` と同じです（CLI 引数 > 環境変数 > デフォルト）。
	- 使い方例:

```powershell
poetry run python scripts/databaseSetup/teardown_sqlite.py
# または
poetry run python scripts/databaseSetup/teardown_sqlite.py F:\path\to\mydb.db
```

- **ensure_sqlite_tables.py** — アプリの SQLAlchemy `Base.metadata` に定義されたテーブルが DB に存在するかを確認し、欠けているテーブルがあれば `create_all` で作成します。
	- `setup_sqlite.py` から呼ばれることを想定していますが、単体で実行しても動作します。

## 注意点

- 既存の `setup_sqlite.bat` / `setup_sqlite.sh` / `teardown_sqlite.bat` は Python 実装に置き換えられています。リポジトリからは削除済みです。
- Windows での `setx` による恒久的な `DATABASE_URL` 設定は副作用があるため、CI や共有環境で実行する際は `--no-persist` を利用してください。
- これらのスクリプトはローカル開発用の補助ツールです。運用環境で DB を変更・削除する際は必ず手順を確認し、HITL（人による確認）を行ってください。

## 追加の運用例

- 仮想環境を使わずにシステム Python で実行する場合は `poetry run` を外して `python` を直接使えます。`poetry run` を推奨します。
- スクリプトを CI で実行する際は `--no-persist` を付け、必要ならば `DATABASE_URL` を環境変数として CI の設定に直接セットしてください。

---
更新: 2026-03-12 — スクリプトを Python 化し、既存バッチを削除しました。
