# SQLite 移行 — UPSERT 方針と実装計画

## 概要
SQLite へ移行する際の最優先対応は UPSERT（ON CONFLICT）周りの互換化です。本書は既存コード（Postgres 方言の `insert(...).on_conflict_do_update()` を多用）を最小限の変更で SQLite に対応させるための方針、実装手順、テスト手順をまとめます。

## 推奨方針（要点）
- 優先方針: 方言ベースの `insert` を使って1ステートメントUPSERTを維持する（性能重視）。
- 補助方針: 方言実行が不可能／失敗した場合は SELECT→INSERT/UPDATE にフォールバックする（互換性確保）。

## 変更概要（短く）
1. `app/utils/db_compat.py` を追加して方言に応じた `insert()` を返すヘルパを実装する。
2. 主要リポジトリを順次修正して `from sqlalchemy.dialects.postgresql import insert` を直接使わず、`db_compat.dialect_insert(...)` を使う。
   - 優先対象: `app/repositories/stock_data_repository.py`, `app/repositories/stock_master_repository.py`
3. 必要に応じてフォールバックロジック（例外捕捉→SELECT/INSERT/UPDATE）を追加する。
4. 単体/統合テストを修正・追加して insert/update の両パスを検証する。

## `app/utils/db_compat.py` (サンプル)
```python
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine
from app.utils.config import get_settings


def dialect_insert(table, engine: Engine | None = None):
    """与えられたエンジンまたは設定に基づき方言insertを返す。

    engine が与えられれば `engine.dialect.name` で判定し、無ければ設定から URL を読む。
    """
    # エンジン優先判定
    if engine is not None:
        name = getattr(engine.dialect, "name", "")
        if name and "sqlite" in name:
            return sqlite_insert(table)
        return pg_insert(table)

    settings = get_settings()
    db_url = getattr(settings, "DATABASE_URL", "")
    if db_url.startswith("sqlite"):
        return sqlite_insert(table)
    return pg_insert(table)
```

## リポジトリの変更例
- 変更前:
```py
from sqlalchemy.dialects.postgresql import insert
stmt = insert(self.model).values(data)
stmt = stmt.on_conflict_do_update(index_elements=[...], set_={...})
```
- 変更後:
```py
from app.utils.db_compat import dialect_insert
table = self.model.__table__
stmt = dialect_insert(table).values(data)
stmt = stmt.on_conflict_do_update(index_elements=[...], set_={...})
```
- 備考: `index_elements` に指定しているカラム名が DB の UNIQUE/INDEX 設定と一致することを事前確認する。

## フォールバック実装（概要）
- `execute(stmt)` を試し、例外（方言固有のエラー、または `NotImplementedError` 相当）を捕捉したら次を行う:
  1. SELECT で既存レコードの存在を確認
  2. 存在する場合は UPDATE、存在しない場合は INSERT
  3. 排他を考慮して再試行ロジック（簡易: リトライ3回、間隔短め）を入れる

## テスト手順（ローカルでの素早い検証）
1. 仮想環境を用意（既存の .venv を利用可）
2. 必要パッケージの追加（SQLite 非同期利用時）:
```bash
poetry add aiosqlite
poetry remove asyncpg
poetry lock
poetry install
```
3. 単体テスト（対象ファイルのみ）を実行:
```bash
# 例: stock_data_repository の upsert に関連するテスト
poetry run pytest tests/unit/repositories/test_stock_data_repository.py -q
```
4. SQLite エンジンで簡易統合テストを実行（in-memory またはファイル）:
```bash
# 予約: このプロジェクトでは既に in-memory SQLite を使うテストがある
poetry run pytest tests/unit/services/views/latest_stocks/test_latest_stocks_refresh.py -q
```

## Alembic / マイグレーション周りの注意
- `INDEX`/`UNIQUE` 定義が UPSERT の `index_elements` と一致していることを必ず確認。
- `server_default=sa.text("now()")` は SQLite 用に `sa.text("(datetime('now'))")` などへ置換が必要。
- オプション: マイグレーションを全削除して `alembic revision --autogenerate` で SQLite 用に再生成（履歴を失うためチーム合意が必要）。

## リスクと緩和
- リスク: SELECT→UPDATE フォールバックは大量データで性能劣化。緩和: チャンク化／バッチ処理設計、ローカル負荷試験。
- リスク: 同時書き込みで `database is locked` が発生。緩和: 書き込み並列数制限、アプリ層でキュー化。

## 推定作業時間（ざっくり）
- `db_compat` 実装 + 1 リポジトリ対応 + 単体テスト修正: 0.5〜1.0 人日
- 主要リポジトリ 3 本対応とテスト確認: 1.5〜2.5 人日
- Alembic マイグレーション修正 / テスト全体: 1〜2 人日（範囲次第）

## ロールアウト手順（簡潔）
1. `app/utils/db_compat.py` を追加する（PR）
2. `stock_data_repository.py` を方言対応に修正して PR（CI でユニットテストを通す）
3. 続けて `stock_master_repository.py` を対応
4. テスト、ローカル負荷（簡易バルク）を実行して `database is locked` 等を検証
5. `app/utils/config.py` / `app/utils/database.py` の SQLite 切替を適用（最終段階）

---
このドキュメントの内容を元に実装パッチを作成できます。どのリポジトリから着手しましょうか（推奨: `stock_data_repository.py`）?
