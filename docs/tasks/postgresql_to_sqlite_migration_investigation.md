---
category: tasks
type: investigation
priority: low
ai_context: high
last_updated: 2026-01-31
related_docs:
  - ../architecture/architecture_overview.md
  - ../architecture/layers/data_storage_layer.md
  - ../develop-guide/development-workflow.md
---

# PostgreSQL → SQLite 移行調査レポート

## 概要
本プロジェクトのデータベースをPostgreSQLからSQLiteへ移行する場合に必要な対処と工数について調査した結果をまとめたものです。

**調査日:** 2026年1月31日
**優先度:** 🟡 Low（推奨しない）
**想定工数:** 7〜8人日（1〜1.5週間）

---

## 調査結果サマリー

### 結論
**現プロジェクトの規模と機能を考慮すると、PostgreSQLのまま継続することを強く推奨します。**

#### 理由
1. マテリアライズドビューの多用（SQLite非対応）
2. UPSERT（ON CONFLICT）の多用（SQLite実装が複雑）
3. 大量データの一括処理性能が重要
4. 並行処理性能の要件

#### SQLite移行が検討可能なケース
- 開発環境の簡略化のみが目的（Dockerで解決可能）
- 小規模デモ環境（機能制限を許容）
- 教育目的のみ

---

## 📋 必要な修正箇所と対処内容

### 1. データベース接続設定の変更

**工数:** 0.5人日
**難易度:** ★☆☆

#### 対象ファイル
- `app/utils/database.py`
- `app/utils/config.py`
- `alembic/env.py`

#### 修正内容

##### 1.1 database.py - 接続URL生成

```python
# 現状（PostgreSQL）
def get_database_url() -> str:
    settings = get_settings()
    return (
        f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )

# 修正後（SQLite）
def get_database_url() -> str:
    settings = get_settings()
    db_path = settings.DB_PATH or "data/stock_analyzer.db"
    return f"sqlite+aiosqlite:///{db_path}"
```

##### 1.2 database.py - エンジン作成

```python
# 現状（PostgreSQL）
engine = create_async_engine(
    database_url,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# 修正後（SQLite）
engine = create_async_engine(
    database_url,
    echo=settings.DEBUG,
    # SQLiteは接続プール設定不要
    connect_args={"check_same_thread": False},  # 非同期用
)
```

##### 1.3 config.py - 設定クラス

```python
# 現状（PostgreSQL）
DB_HOST: str = Field(..., description="Database host")
DB_PORT: int = Field(..., description="Database port")
DB_NAME: str = Field(..., description="Database name")
DB_USER: str = Field(..., description="Database user")
DB_PASSWORD: str = Field(..., description="Database password")
DB_POOL_SIZE: int = Field(5, description="SQLAlchemy engine pool size")
DB_MAX_OVERFLOW: int = Field(10, description="SQLAlchemy engine max overflow")

# 修正後（SQLite）
DB_PATH: str = Field("data/stock_analyzer.db", description="SQLite database file path")
# 接続プール設定は削除
```

##### 1.4 alembic/env.py - マイグレーションURL

```python
# 現状（PostgreSQL）
def get_alembic_database_url() -> str:
    settings = get_settings()
    return (
        f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )

# 修正後（SQLite）
def get_alembic_database_url() -> str:
    settings = get_settings()
    db_path = settings.DB_PATH or "data/stock_analyzer.db"
    return f"sqlite+aiosqlite:///{db_path}"
```

---

### 2. PostgreSQL固有機能の対応

**工数:** 2人日
**難易度:** ★★★

#### 2.1 UUID型の置き換え

**対象ファイル:**
- `app/models/base.py`

**現状:**
```python
from sqlalchemy.dialects.postgresql import UUID as PGUUID

class UUIDPKMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
```

**修正方法（オプション1: String型で保存）:**
```python
import uuid
from sqlalchemy import String, TypeDecorator

class UUIDType(TypeDecorator):
    """SQLite用のUUID型デコレータ"""
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return uuid.UUID(value)

class UUIDPKMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, primary_key=True, default=uuid.uuid4
    )
```

**注意:**
- 現状、`UUIDPKMixin` は定義されているが実際のモデルで使用されていない可能性が高い
- 実際の使用状況を確認してから対処方法を決定すること

#### 2.2 UPSERT（ON CONFLICT）の書き換え

**対象ファイル:**
- `app/repositories/stock_data_repository.py` - `upsert_single` メソッド
- `app/repositories/edinet_balance_sheet_repository.py` - `upsert` メソッド

**現状（PostgreSQL）:**
```python
# stock_data_repository.py
stmt = insert(self.model).values(data)
stmt = stmt.on_conflict_do_update(
    index_elements=["symbol", self.time_column],
    set_=update_values
)
result = await self.session.execute(stmt)
```

**修正方法（オプション1: INSERT OR REPLACE）:**
```python
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

# SQLite用
stmt = sqlite_insert(self.model).values(data)
stmt = stmt.on_conflict_do_update(
    index_elements=["symbol", self.time_column],
    set_=update_values
)
result = await self.session.execute(stmt)
```

**修正方法（オプション2: SELECT → INSERT/UPDATE）:**
```python
async def upsert_single(self, data: dict) -> dict:
    # 既存レコードをチェック
    existing = await self.session.execute(
        select(self.model).where(
            self.model.symbol == data["symbol"],
            getattr(self.model, self.time_column) == data[self.time_column]
        )
    )
    record = existing.scalar_one_or_none()

    if record:
        # UPDATE
        for key, value in data.items():
            setattr(record, key, value)
        operation = "update"
    else:
        # INSERT
        record = self.model(**data)
        self.session.add(record)
        operation = "insert"

    await self.session.flush()
    return {"operation": operation, "rowcount": 1, ...}
```

**性能への影響:**
- オプション1: PostgreSQLと同等の性能（SQLAlchemy 1.4以降でサポート）
- オプション2: 2回のクエリが必要なため性能低下（大量処理で顕著）

#### 2.3 マテリアライズドビュー対応

**対象ファイル:**
- `app/services/views/latest_stocks/refresh.py`
- `alembic/versions/b7f3c1a2d9e4_create_latest_stocks_1d.py`

**現状（PostgreSQL）:**
```python
# refresh.py
await conn.execute(
    text("REFRESH MATERIALIZED VIEW CONCURRENTLY latest_stocks_1d;")
)
```

**問題点:**
SQLiteはマテリアライズドビューをサポートしていない

**修正方法（オプション1: 通常のVIEWに変更）:**
```python
# マイグレーション
def upgrade():
    op.execute("""
        CREATE VIEW latest_stocks_1d AS
        SELECT ... (クエリ内容は同じ)
    """)

# サービス
async def run_refresh(self) -> None:
    # VIEWは自動更新されるため処理不要
    self.logger.info("latest_stocks_1d is a VIEW (auto-updated)")
```

**メリット:** 実装がシンプル
**デメリット:** 毎回クエリ実行、パフォーマンス低下

**修正方法（オプション2: テーブル＋定期再構築）:**
```python
# マイグレーション
def upgrade():
    op.create_table(
        'latest_stocks_1d',
        sa.Column('symbol', sa.String(10), nullable=False),
        # ... 必要なカラム
        sa.PrimaryKeyConstraint('symbol')
    )

    # 初期データ投入用トリガーなど

# サービス
async def run_refresh(self) -> None:
    # テーブル内容を再構築
    await conn.execute(text("DELETE FROM latest_stocks_1d;"))
    await conn.execute(text("""
        INSERT INTO latest_stocks_1d
        SELECT ... (クエリ内容)
    """))
    await conn.commit()
```

**メリット:** パフォーマンス維持
**デメリット:** 実装が複雑、トランザクション管理が必要

**修正方法（オプション3: アプリケーション層キャッシュ）:**
```python
from functools import lru_cache
from datetime import datetime, timedelta

class LatestStocksCache:
    _cache = None
    _last_refresh = None
    _cache_duration = timedelta(hours=1)

    @classmethod
    async def get_latest_stocks(cls, session):
        now = datetime.now()
        if cls._cache is None or \
           (now - cls._last_refresh) > cls._cache_duration:
            # キャッシュを更新
            result = await session.execute(text("SELECT ... (クエリ)"))
            cls._cache = result.fetchall()
            cls._last_refresh = now
        return cls._cache
```

**メリット:** DBへの負荷軽減
**デメリット:** メモリ使用、分散環境で不整合の可能性

---

### 3. Alembicマイグレーションの再生成

**工数:** 1人日
**難易度:** ★★☆

#### 対象ファイル
`alembic/versions/` 配下の全8ファイル:
- `4e581533f2e4_initial_database_schema.py`
- `5eb81fa2fa7a_feat_db_add_tables_for_batch_execution_.py`
- `892e1f109de2_add_accounts_account_transactions_.py`
- `a34daef60fc9_add_new_models.py`
- `b7f3c1a2d9e4_create_latest_stocks_1d.py`
- `c1f9d2b3e4f5_merge_heads_0d5d_b7f3.py`
- `d5a1c2b3e4f6_add_edinet_balance_sheets_table.py`
- `0d5d2098df45_add_stock_master_updates_handling.py`

#### 修正が必要な箇所

##### 3.1 server_default の修正

**現状（PostgreSQL）:**
```python
sa.Column(
    "created_at",
    sa.DateTime(timezone=True),
    server_default=sa.text("now()"),  # PostgreSQL関数
    nullable=False,
)
```

**修正後（SQLite）:**
```python
sa.Column(
    "created_at",
    sa.DateTime(timezone=True),
    server_default=sa.text("(datetime('now'))"),  # SQLite関数
    nullable=False,
)
```

##### 3.2 マテリアライズドビューの削除/変更

**対象:** `b7f3c1a2d9e4_create_latest_stocks_1d.py`

```python
# 現状（PostgreSQL）
def upgrade():
    op.execute("""
        CREATE MATERIALIZED VIEW latest_stocks_1d AS ...
    """)
    op.execute("CREATE UNIQUE INDEX ...")

# 修正後（SQLite - 通常のVIEWに変更）
def upgrade():
    op.execute("""
        CREATE VIEW latest_stocks_1d AS ...
    """)
    # VIEWにはINDEX不要
```

##### 3.3 推奨アプローチ

**オプションA: マイグレーションファイルを個別修正**
- 各ファイルのPostgreSQL固有構文を修正
- メリット: マイグレーション履歴を維持
- デメリット: 手作業が多く、ミスのリスク

**オプションB: マイグレーションを初期化**
```bash
# 既存マイグレーションを削除
rm -rf alembic/versions/*

# 現在のモデル定義から新規マイグレーション生成
alembic revision --autogenerate -m "initial_schema_sqlite"

# SQLite用に生成されたファイルを確認・修正
```
- メリット: 確実、最新のモデル定義を反映
- デメリット: 既存のマイグレーション履歴が失われる

**推奨:** プロジェクトが開発初期段階のため、オプションBを推奨

---

### 4. 依存パッケージの変更

**工数:** 0.5人日
**難易度:** ★☆☆

#### 対象ファイル
- `pyproject.toml`

#### 修正内容

```toml
[tool.poetry.dependencies]
# 削除するパッケージ
# asyncpg = "0.31.0"  ← 削除

# 追加するパッケージ
aiosqlite = "^0.20.0"  # SQLite非同期ドライバ

# 以下はそのまま維持
sqlalchemy = { version = "2.0.44", extras = ["asyncio"] }

[tool.poetry.group.dev.dependencies]
# 削除するパッケージ
# psycopg = { version = "^3.2", extras = ["binary"] }  ← 削除

# その他の開発用パッケージはそのまま
```

#### インストール手順

```bash
# 古いパッケージを削除
poetry remove asyncpg
poetry remove psycopg --group dev

# 新しいパッケージを追加
poetry add aiosqlite

# 依存関係を更新
poetry lock
poetry install
```

---

### 5. テストの修正

**工数:** 1人日
**難易度:** ★★☆

#### 5.1 database.py のユニットテスト

**対象:** `tests/unit/utils/test_database.py`

```python
# 現状（PostgreSQL）
def test_get_database_url_returns_correct_format(self, mock_settings):
    # ... モック設定
    url = get_database_url()
    assert url == (
        "postgresql+asyncpg://test_user:test_password"
        "@localhost:5432/test_db"
    )

# 修正後（SQLite）
def test_get_database_url_returns_correct_format(self, mock_settings):
    mock_settings.DB_PATH = "test_data/test.db"
    url = get_database_url()
    assert url == "sqlite+aiosqlite:///test_data/test.db"
```

#### 5.2 E2Eテストの設定

**対象:** `tests/e2e/conftest.py`

```python
# 現状（PostgreSQL）
def is_db_reachable() -> bool:
    # ソケット接続でDB到達性チェック
    try:
        with socket.create_connection((host, int(port)), timeout=1):
            return True
    except Exception:
        return False

# 修正後（SQLite）
def is_db_reachable() -> bool:
    # SQLiteはファイルベースなので、ファイルの存在チェック
    try:
        from app.utils.config import get_settings
        settings = get_settings()
        db_path = settings.DB_PATH
        # ファイルが存在しない場合は作成される想定なので常にTrue
        return True
    except Exception:
        return False
```

#### 5.3 統合テストの設定

**対象:** `tests/integration/conftest.py`

現状の実装（エンジンキャッシュクリア）はSQLiteでもそのまま使用可能。
修正不要。

#### 5.4 モデルのユニットテスト

**対象:** `tests/unit/models/test_batch_execution.py` など

```python
# 現状（PostgreSQL互換のSQLiteを使用中）
engine = create_engine("sqlite:///:memory:", future=True)
```

現状既にSQLiteを使用しているため、修正不要。

---

### 6. ドキュメント・セットアップスクリプトの更新

**工数:** 0.5人日
**難易度:** ★☆☆

#### 6.1 ドキュメントの更新

**対象ファイル:**
- `docs/setup/SETUP.md`（未作成の場合は新規作成）
- `docs/architecture/layers/data_storage_layer.md`
- `README.md`

**修正内容:**
- PostgreSQLのインストール手順 → 削除
- SQLiteの使用方法を追記
- 環境変数の設定例を更新（`.env.example`）

#### 6.2 セットアップスクリプトの更新

**対象:**
- `scripts/databaseSetup/setup_db.sh`
- `scripts/databaseSetup/setup_db.bat`
- `scripts/databaseSetup/teardown_db.sh`

**修正内容:**
```bash
# 現状（PostgreSQL）
echo "Checking PostgreSQL installation..."
psql --version || {
    echo "PostgreSQL client not found"
    exit 1
}

# 修正後（SQLite）
echo "Checking SQLite installation..."
sqlite3 --version || {
    echo "SQLite not found"
    exit 1
}

# データベース作成
# PostgreSQL: psql -U postgres -c "CREATE DATABASE ..."
# SQLite: ファイル作成（Alembicが自動生成）
echo "Database file will be created by Alembic migrations"
```

#### 6.3 環境変数テンプレート

**対象:** `.env.example`（新規作成）

```bash
# PostgreSQL用（現状）
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stock_analyzer
DB_USER=stock_user
DB_PASSWORD=your_password_here
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# SQLite用（修正後）
DB_PATH=data/stock_analyzer.db
# 接続プール設定は不要
```

---

## ⏱️ 総工数見積もり

| 項目                        | 工数             | 難易度 | 備考                           |
| --------------------------- | ---------------- | ------ | ------------------------------ |
| 1. DB接続設定の変更         | 0.5人日          | ★☆☆    | 比較的単純                     |
| 2. PostgreSQL固有機能の対応 | 2人日            | ★★★    | UPSERT、マテリアライズドビュー |
| 3. Alembicマイグレーション  | 1人日            | ★★☆    | 初期化推奨                     |
| 4. 依存パッケージの変更     | 0.5人日          | ★☆☆    | Poetryで自動                   |
| 5. テストの修正             | 1人日            | ★★☆    | 全テストの動作確認必要         |
| 6. ドキュメント更新         | 0.5人日          | ★☆☆    | 手順書の書き換え               |
| **小計**                    | **5.5人日**      | -      | -                              |
| **リスクバッファ（30%）**   | **1.5〜2.5人日** | -      | 想定外の問題対応               |
| **合計**                    | **7〜8人日**     | -      | **約1〜1.5週間**               |

---

## ⚠️ リスクと制限事項

### 技術的リスク

#### 1. マテリアライズドビューの制約
- **問題:** SQLiteは非対応
- **影響:** パフォーマンス低下、実装の複雑化
- **対策案:**
  - 通常のVIEWに変更（クエリ実行時間増加を許容）
  - アプリケーション層キャッシュ（メモリ使用量増加）
  - 定期的なテーブル再構築（バッチ処理追加）

#### 2. UPSERT性能
- **問題:** PostgreSQLの`ON CONFLICT`より効率が落ちる
- **影響:** 大量データの一括処理で速度低下（特に株価データ）
- **定量評価:** 10,000件のバルクUPSERTで約2〜3倍の処理時間が想定される

#### 3. 並行処理性能
- **問題:** SQLiteはライトロック（1トランザクション/時刻）
- **影響:**
  - 複数バッチの同時実行が不可
  - APIリクエストとバッチ処理の競合
- **制限:** 最大1ライター、複数リーダー

#### 4. UUIDサポート
- **問題:** ネイティブ型がなく、String(36)で代用
- **影響:**
  - インデックス効率の若干の低下
  - ストレージ容量の増加（約4倍）

#### 5. データベースサイズ制限
- **SQLiteの理論上限:** 約281TB（実用上は数GB〜数十GB推奨）
- **本プロジェクト想定:**
  - 株価データ: 4,000銘柄 × 10年 × 4テーブル ≈ 数GB
  - 問題になる可能性は低いが、運用上の監視が必要

### 運用リスク

#### 1. バックアップ・リストア
- **PostgreSQL:** `pg_dump`/`pg_restore`（差分バックアップ可能）
- **SQLite:** ファイルコピー（差分が難しい）

#### 2. 本番環境での使用
- **推奨しない理由:**
  - 並行書き込み性能が低い
  - トランザクション分離レベルの制限
  - 大規模データでのパフォーマンス劣化

#### 3. 移行戻しの困難さ
- SQLite → PostgreSQL の移行も工数が必要
- 本番データ移行時のダウンタイム

---

## 📝 推奨事項

### ✅ PostgreSQL継続を推奨する理由

1. **現状の設計が最適化されている**
   - マテリアライズドビュー、UPSERT多用
   - 大量データの効率的な処理

2. **スケーラビリティ**
   - 将来的なデータ増加に対応可能
   - 並行処理性能が高い

3. **開発環境の簡略化は他の手段で解決可能**
   ```yaml
   # docker-compose.yml で簡単にPostgreSQL起動
   version: '3.8'
   services:
     postgres:
       image: postgres:15
       environment:
         POSTGRES_DB: stock_analyzer
         POSTGRES_USER: stock_user
         POSTGRES_PASSWORD: password
       ports:
         - "5432:5432"
   ```

4. **本番環境での信頼性**
   - 実績のあるDBMS
   - 豊富な監視ツール

### 🟡 SQLite移行が許容できるケース

以下の**全ての条件**を満たす場合のみ検討可能：

1. **開発・デモ環境限定**（本番使用は不可）
2. **データ量が少ない**（1,000銘柄未満、1年分以下）
3. **バッチ処理の並行実行なし**
4. **マテリアライズドビューの代替実装を許容**
5. **パフォーマンス低下を許容**（2〜3倍遅くてもOK）

---

## 📚 参考情報

### SQLite vs PostgreSQL 性能比較

| 項目         | PostgreSQL             | SQLite                   | 影響       |
| ------------ | ---------------------- | ------------------------ | ---------- |
| 同時書き込み | ◎ 高性能               | △ 1トランザクション/時刻 | バッチ処理 |
| UPSERT性能   | ◎ ネイティブ           | ○ エミュレーション       | 処理時間   |
| ビュー       | ◎ マテリアライズド対応 | △ 通常のみ               | クエリ性能 |
| インデックス | ◎ 豊富な種類           | ○ 基本的なもの           | 検索性能   |
| データサイズ | ◎ TB級                 | ○ GB級推奨               | スケール   |
| セットアップ | △ やや複雑             | ◎ 簡単                   | 開発環境   |

### 関連ドキュメント

- [SQLAlchemy SQLite Dialect Documentation](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html)
- [aiosqlite Documentation](https://aiosqlite.omnilib.dev/)
- [SQLite Limitations](https://www.sqlite.org/limits.html)

---

## 次のステップ

### SQLite移行を進める場合

1. ✅ Issue化（本ドキュメント）
2. 🔲 PoC（Proof of Concept）の実施
   - 小規模なテストデータで性能検証
   - マテリアライズドビューの代替実装検証
3. 🔲 段階的な実装（前述の1〜6の順）
4. 🔲 全テストの実行と結果検証
5. 🔲 パフォーマンステストの実施
6. 🔲 ドキュメント更新とレビュー

### PostgreSQL継続を選択する場合（推奨）

1. ✅ 本ドキュメントをアーカイブ
2. 🔲 Docker Compose環境の整備
3. 🔲 開発環境セットアップドキュメントの改善
4. 🔲 CI/CD環境でのPostgreSQL利用最適化

---

## 関連Issue

- なし（新規調査）

---

**結論:** 本プロジェクトの規模と要件を考慮すると、**PostgreSQLの継続使用を強く推奨**します。開発環境の簡略化が目的であれば、Docker Composeの活用が最適なソリューションです。
