# 日経225構成銘柄リスト実装仕様書

## 概要

### 目的
- 日経225の公式CSVから構成銘柄リストを取得し、DBに同期
- STOCK_MASTER更新時に自動的に日経225テーブルも更新される設計
- Yahoo Finance ティッカーから「この銘柄は日経225に含まれるか？」を判定可能にする

### データソース
- **URL**: https://indexes.nikkei.co.jp/nkave/archives/file/nikkei_225_price_adjustment_factor_jp.csv
- **エンコーディング**: Shift_JIS
- **更新頻度**: 毎営業日
- **レコード数**: 225銘柄 + 1ヘッダー行

---

## ER図設計

### テーブル: NIKKEI225_COMPONENTS

```
NIKKEI225_COMPONENTS
├── id (PK)                           [INTEGER]
├── stock_code (FK → STOCK_MASTER)    [VARCHAR(4), NOT NULL]
├── price_adjustment_factor            [NUMERIC(5,1), NOT NULL]
├── effective_date                     [DATE, NOT NULL]
├── created_at                         [DATETIME]
└── updated_at                         [DATETIME]

Unique Constraints:
  ├─ PRIMARY: id
  └─ UNIQUE: (stock_code, effective_date)   ← 銘柄の履歴トラッキング

Indices:
  ├─ idx_nikkei225_stock_code        [stock_code]
  └─ idx_nikkei225_effective_date    [effective_date]

Relationships:
  └─ STOCK_MASTER.stock_code ← 1:N → NIKKEI225_COMPONENTS.stock_code
```

### CSVカラム対応表

| CSV カラム | DB カラム | 説明 | 保存 |
|-----------|---------|------|------|
| 対象日付 | effective_date | 日経225の構成銘柄更新日 | ✅ |
| コード | stock_code | 4桁銘柄コード | ✅ |
| 銘柄名 | - | STOCK_MASTER.stock_name で取得可能 | ✗ |
| 株価換算係数 | price_adjustment_factor | 指数計算用（0.1～24.0） | ✅ |
| 業種 | - | STOCK_MASTER.sector で取得可能 | ✗ |
| セクター | - | STOCK_MASTER.sector で取得可能 | ✗ |

---

## 設計原則

### 1. 正規化
- 銘柄属性（名称、業種、セクター）は **STOCK_MASTER で一元管理**
- NIKKEI225_COMPONENTS は構成メンバーシップのみを保持

### 2. 履歴トラッキング
- 複合UK `(stock_code, effective_date)` で銘柄の入れ替わり履歴を追跡可能
- 将来的に過去データ遡及対応が容易

### 3. 自動更新連携
- STOCK_MASTER更新API (`POST /fetch`) 実行時に日経225も自動更新
- エラーハンドリング: 日経225更新失敗時も STOCK_MASTER は成功のままで進行

---

## 実装アーキテクチャ

### 層構造

```
API層
  ├─ POST /fetch (既存のSTOCK_MASTER更新API)
  │   └─ 内部: StockMasterService.fetch_and_save()
  │       └─ 最後に自動実行: Nikkei225ComponentsService.fetch_and_update()
  │
API レスポンス
  └─ {
      "message": "Stock master fetch completed",
      "updated_count": 1500,
      "nikkei225": {                 ← [NEW]
        "success": true,
        "count": 225,
        "error": null
      }
    }
```

### サービス呼び出しチェーン

```
StockMasterService.fetch_and_save()
  │
  ├─ [既存] JPXからSTOCK_MASTER取得 → DB保存
  ├─ [既存] マスターテーブル（業種、市場カテゴリ等）作成
  ├─ [既存] stock_code_mapping保存
  │
  └─ [NEW] Nikkei225ComponentsService.fetch_and_update()  ← 自動連携
       ├─ 公式CSVダウンロード
       ├─ パース
       └─ DB保存（UPSERT）
```

---

## ファイル構成

### Phase 1: DB層（2時間）

```
app/
├── models/market_data/nikkei225/
│   ├── __init__.py                           [New]
│   └── nikkei225_components.py               [New]
│       └── class Nikkei225Component
│
├── schemas/market_data/nikkei225/
│   ├── __init__.py                           [New]
│   └── nikkei225_components.py               [New]
│       ├── class Nikkei225ComponentCreate
│       └── class Nikkei225ComponentRead
│
└── repositories/market_data/nikkei225/
    ├── __init__.py                           [New]
    └── nikkei225_components_repository.py    [New]
        └── class Nikkei225ComponentRepository
            ├── upsert_batch()
            └── find_by_code()

alembic/versions/
└── YYYYMMDD_hhmmss_add_nikkei225_components_table.py   [New]
```

### Phase 2: ビジネスロジック層（2時間）

```
app/
├── services/market_data/nikkei225/
│   ├── __init__.py                           [New]
│   └── nikkei225_components_service.py       [New]
│       └── class Nikkei225ComponentsService
│           ├── fetch_and_update()
│           ├── is_in_nikkei225()
│           └── get_component_info()
│
├── utils/
│   ├── nikkei225_matcher.py                  [New]
│       └── class Nikkei225Matcher
│           ├── yahoo_ticker_to_code()
│           ├── is_nikkei225()
│           └── get_nikkei225_info()
│
└── services/data_synchronization/market_data/stock_master/
    └── service.py                            [Modified]
        └── fetch_and_save(): 最後に日経225を自動実行
```

### Phase 3: テスト層（2時間）

```
tests/
├── unit/
│   ├── test_nikkei225_matcher.py             [New]
│   ├── test_nikkei225_repository.py          [New]
│   └── test_nikkei225_service.py             [New]
│
└── e2e/
    └── test_nikkei225_fetch_integration.py   [New]
```

---

## 実装詳細

### 1. Model (`app/models/market_data/nikkei225/nikkei225_components.py`)

```python
from datetime import date
from decimal import Decimal
from sqlalchemy import ForeignKey, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.core.base import Base, SerialPKMixin, TimestampMixin

class Nikkei225Component(SerialPKMixin, TimestampMixin, Base):
    """日経225構成銘柄マスター.

    銘柄属性（名称、業種）はSTOCK_MASTERで管理。
    本テーブルは構成メンバーシップと指数計算用係数のみ保有。
    """

    __tablename__ = "nikkei225_components"

    stock_code: Mapped[str] = mapped_column(
        ForeignKey("stock_master.stock_code"),
        nullable=False
    )
    price_adjustment_factor: Mapped[Decimal] = mapped_column(
        Numeric(5, 1),
        nullable=False
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "stock_code",
            "effective_date",
            name="uq_nikkei225_code_date"
        ),
        Index("idx_nikkei225_stock_code", "stock_code"),
        Index("idx_nikkei225_effective_date", "effective_date"),
    )
```

### 2. Schema (`app/schemas/market_data/nikkei225/nikkei225_components.py`)

```python
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

class Nikkei225ComponentCreate(BaseModel):
    stock_code: str = Field(..., min_length=4, max_length=4)
    price_adjustment_factor: Decimal
    effective_date: date

class Nikkei225ComponentRead(Nikkei225ComponentCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### 3. Repository (`app/repositories/market_data/nikkei225/nikkei225_components_repository.py`)

```python
from sqlalchemy import desc, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.market_data.nikkei225 import Nikkei225Component
from app.repositories.core.base import BaseRepository

class Nikkei225ComponentRepository(BaseRepository[Nikkei225Component]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, model=Nikkei225Component)

    async def upsert_batch(self, data_list: list[dict]) -> list[Nikkei225Component]:
        """一括 upsert (stock_code + effective_date で重複判定)."""
        if not data_list:
            return []

        table = self.model.__table__
        insert_stmt = insert(table).values(data_list)
        update_dict = {
            c.name: getattr(insert_stmt.excluded, c.name)
            for c in table.c
            if c.name not in ("id", "created_at")
        }
        stmt = (
            insert_stmt.on_conflict_do_update(
                index_elements=["stock_code", "effective_date"],
                set_=update_dict,
            )
            .returning(table)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return [
            self.model(**dict(row._mapping))
            for row in result.fetchall()
        ]

    async def find_by_code(self, stock_code: str) -> Nikkei225Component | None:
        """銘柄コードで検索（最新日付を返す）."""
        stmt = (
            select(self.model)
            .where(self.model.stock_code == stock_code)
            .order_by(desc(self.model.effective_date))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
```

### 4. Service (`app/services/market_data/nikkei225/nikkei225_components_service.py`)

```python
from datetime import datetime
from pathlib import Path
from typing import Any
import pandas as pd
import requests
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.market_data.nikkei225 import Nikkei225ComponentRepository
from app.services.data_synchronization._core.file_managers import TempFileManagerMixin
from app.utils.logger import get_logger

logger = get_logger(__name__)

class Nikkei225ComponentsService(TempFileManagerMixin):
    """日経225構成銘柄の取得・更新サービス."""

    OFFICIAL_URL = "https://indexes.nikkei.co.jp/nkave/archives/file/nikkei_225_price_adjustment_factor_jp.csv"
    ENCODING = "shift_jis"
    TIMEOUT = 30
    CSV_FILENAME = "nikkei_225_price_adjustment_factor_jp.csv"

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = Nikkei225ComponentRepository(session)

    async def fetch_and_update(self) -> dict[str, Any]:
        """公式CSVを取得してDB更新.

        注意: CSVファイルはJPXエクセルファイルと同様に一時ディレクトリにダウンロード後、
        処理完了時に自動削除される。
        """
        # 一時ディレクトリでコンテキスト管理（処理終了時に自動削除）
        with self.tempdir_context(prefix="nikkei225_") as temp_dir:
            try:
                logger.info("Fetching Nikkei225 components from official source")

                # CSVダウンロード
                response = requests.get(self.OFFICIAL_URL, timeout=self.TIMEOUT)
                response.raise_for_status()
                response.encoding = self.ENCODING

                # 一時ファイルに保存
                csv_path = temp_dir / self.CSV_FILENAME
                csv_path.write_text(response.text, encoding=self.ENCODING)
                logger.info(f"CSV downloaded to temporary file: {csv_path}")

                # CSV パース
                df = pd.read_csv(str(csv_path), encoding=self.ENCODING)

                # データ検証・変換（必要なカラムのみ）
                records = []
                for _, row in df.iterrows():
                    try:
                        records.append({
                            "stock_code": str(row["コード"]).zfill(4),
                            "price_adjustment_factor": float(row["株価換算係数"]),
                            "effective_date": datetime.strptime(
                                str(row["対象日付"]), "%Y/%m/%d"
                            ).date(),
                        })
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Row parse error: {e}, row={row}")
                        continue

                if not records:
                    logger.error("No valid records found in CSV")
                    return {"success": False, "error": "No valid records found", "count": 0}

                logger.info(f"Parsed {len(records)} records from CSV")

                # DB保存
                result = await self.repository.upsert_batch(records)
                await self.session.commit()

                logger.info(f"Successfully saved {len(result)} Nikkei225 components")
                return {"success": True, "count": len(result), "error": None}

            except requests.RequestException as e:
                logger.error(f"Network error fetching Nikkei225 CSV: {e}")
                return {"success": False, "error": f"Network error: {e}", "count": 0}
            except Exception as e:
                logger.exception("Unexpected error in fetch_and_update")
                await self.session.rollback()
                return {"success": False, "error": f"Unexpected error: {e}", "count": 0}
            finally:
                logger.info("Temporary CSV file cleaned up automatically")

    async def is_in_nikkei225(self, stock_code: str) -> bool:
        """銘柄が日経225に含まれるか."""
        component = await self.repository.find_by_code(stock_code.zfill(4))
        return component is not None
```

### 5. Matcher (`app/utils/nikkei225_matcher.py`)

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.market_data.nikkei225 import Nikkei225ComponentsService

class Nikkei225Matcher:
    """Yahoo Finance ティッカー ↔ 日経225 照合ユーティリティ."""

    def __init__(self, session: AsyncSession):
        self.service = Nikkei225ComponentsService(session)

    @staticmethod
    def yahoo_ticker_to_code(yahoo_ticker: str) -> str:
        """Yahoo ティッカーを銘柄コードに変換.

        Examples:
            "7203.T" -> "7203"
            "1332.T" -> "1332"
        """
        return yahoo_ticker.split('.')[0]

    async def is_nikkei225(self, yahoo_ticker: str) -> bool:
        """Yahoo ティッカーが日経225に含まれるか."""
        code = self.yahoo_ticker_to_code(yahoo_ticker)
        return await self.service.is_in_nikkei225(code)
```

### 6. StockMasterService 統合 (`app/services/data_synchronization/market_data/stock_master/service.py`)

修正個所：`fetch_and_save()` メソッドの最後に以下を追加

```python
async def fetch_and_save(self, limit: Optional[int] = None, batch_size: int = 500) -> dict:
    """銘柄マスターをフェッチして保存します.

    [既存の処理省略...]

    新規追加: 日経225構成銘柄も自動更新
    """
    # [既存の処理...]

    # [NEW] 日経225構成銘柄の自動更新
    nikkei225_result = {"success": False, "error": "Skipped"}
    try:
        from app.services.market_data.nikkei225 import Nikkei225ComponentsService
        nikkei225_service = Nikkei225ComponentsService(self.session)
        nikkei225_result = await nikkei225_service.fetch_and_update()
        logger.info(
            "Nikkei225 components update completed",
            extra={"result": nikkei225_result}
        )
    except Exception as e:
        logger.warning(
            "Failed to update Nikkei225 components",
            extra={"error": str(e)}
        )
        nikkei225_result = {"success": False, "error": str(e), "count": 0}

    # レスポンス返却（日経225結果を含める）
    return {
        "stock_master": {
            "updated_count": total_processed,
            "fetch_time": fetch_time,
            "save_time": save_time,
        },
        "nikkei225": nikkei225_result,  ← [NEW]
    }
```

---

## APIレスポンス仕様

### `POST /fetch`（統合レスポンス）

```json
{
  "message": "Stock master fetch completed",
  "updated_count": 1500,
  "nikkei225": {
    "success": true,
    "count": 225,
    "error": null
  }
}
```

### `POST /fetch/sample`（サンプルフェッチ）

```json
{
  "message": "Stock master sample fetch completed (sample_size=100)",
  "updated_count": 100,
  "nikkei225": {
    "success": true,
    "count": 225,
    "error": null
  }
}
```

---

## 何に注意すればよいのか

### 1. 一時ファイル管理
- CSVファイルはJPXのエクセルファイル処理と同様に、**一時ディレクトリにダウンロード**される
- `TempFileManagerMixin.tempdir_context()` でコンテキスト管理し、処理終了時に**自動削除**
- `finally` ブロックでファイル削除が完了されることを確認するため、ログ出力を必ず記載

### 2. エンコーディング
- **Shift_JIS エンコーディング必須**
- `response.encoding = "shift_jis"` で明示的に指定
- ファイル保存時も `write_text(..., encoding="shift_jis")` で統一

### 3. エラーハンドリング
- ネットワークエラー時は日経225更新失敗を返す（STOCK_MASTER は成功のまま）
- CSV パース失敗時も親処理に影響させない
- `await self.session.rollback()` で不完全なトランザクションをロールバック

---

## 参考実装パターン

### JPXエクセルファイル処理との類似性

| 項目 | JPXエクセル | 日経225CSV |
|------|-----------|----------|
| ダウンロード元 | JPX公式サイト | 日経公式サイト |
| ファイル形式 | Excel (.xlsx) | CSV (Shift_JIS) |
| 一時ディレクトリ | `TempFileManagerMixin` で管理 | `TempFileManagerMixin` で管理 |
| 自動削除 | `tempdir_context()` の終了時 | `tempdir_context()` の終了時 |
| エラーハンドリング | ネットワーク→ログ記録 | ネットワーク→ログ記録 |
| 本体への影響 | 独立したサービス層 | 独立したサービス層 |

---

### Phase 3: ユニットテスト

#### `tests/unit/test_nikkei225_matcher.py`
```python
□ test_yahoo_ticker_to_code()
□ test_is_nikkei225_valid()
□ test_is_nikkei225_invalid()
```

#### `tests/unit/test_nikkei225_service.py`
```python
□ test_fetch_and_update_success()
□ test_fetch_and_update_network_error()
□ test_is_in_nikkei225()
```

#### `tests/unit/test_nikkei225_repository.py`
```python
□ test_upsert_batch_insert()
□ test_upsert_batch_update_on_duplicate()
□ test_find_by_code_latest()
```

### E2Eテスト

#### `tests/e2e/test_nikkei225_fetch_integration.py`
```python
□ test_fetch_and_save_with_nikkei225_integration()
  - STOCK_MASTER APIを呼び出す
  - 日経225テーブルが自動更新されることを確認
  - 225銘柄がDB保存されることを検証
```

---

## 実装チェックリスト

### Phase 1: DB層
- [ ] Model作成 → `app/models/market_data/nikkei225/nikkei225_components.py`
- [ ] Schema作成 → `app/schemas/market_data/nikkei225/nikkei225_components.py`
- [ ] Repository作成 → `app/repositories/market_data/nikkei225/nikkei225_components_repository.py`
- [ ] `__init__.py` 作成（models, schemas, repositories各層）
- [ ] マイグレーション実行
  ```bash
  poetry run alembic revision --autogenerate -m "Add nikkei225_components table"
  poetry run alembic upgrade head
  ```
- [ ] DBにテーブル作成確認
  ```bash
  sqlite3 app.db ".schema nikkei225_components"
  ```

### Phase 2: ビジネスロジック層
- [ ] Service作成 → `app/services/market_data/nikkei225/nikkei225_components_service.py`
  - [ ] `TempFileManagerMixin` を継承確認
  - [ ] `tempdir_context()` でコンテキスト管理
  - [ ] CSVダウンロード → ファイル保存 → 処理 → 自動削除のフロー確認
- [ ] Matcher作成 → `app/utils/nikkei225_matcher.py`
- [ ] Service統合 → `StockMasterService.fetch_and_save()` に日経225呼び出し追加
- [ ] APIレスポンス修正（日経225結果を含める）
- [ ] 機能テスト実施
  ```bash
  poetry run pytest tests/unit/test_nikkei225_matcher.py -v
  poetry run pytest tests/unit/test_nikkei225_service.py -v
  ```

### Phase 3: 統合テスト
- [ ] StockMasterAPI呼び出しでNikkei225も更新されることを確認
- [ ] E2Eテスト作成・実行
  ```bash
  poetry run pytest tests/e2e/test_nikkei225_fetch_integration.py -v
  ```
- [ ] エラーハンドリング（日経225失敗時もSTOCK_MASTERは成功）を検証

---

## トラブルシューティング

### Q: 一時ファイルが削除されない
A: `tempdir_context()` が `finally` ブロック内で実行され、必ず削除される設計です。ログに "Temporary CSV file cleaned up automatically" が出ていることを確認してください。

### Q: CSV取得がタイムアウト
A: `TIMEOUT = 30` を増やすか、ネットワーク接続を確認

### Q: エンコーディングエラー
A: Shift_JIS でなく cp932 または iso-2022-jp を試す

### Q: 銘柄が日経225から外れたら？
A: 古いレコードはDBに残る。`find_by_code()` は常に最新日付を返すので問題なし。

### Q: 過去データまで遡及したい？
A: `effective_date` で時系列管理されているので、データ投入するだけで対応可能。

---

## 参考情報

### ER図
- `docs/architecture/diagrams/er.md` に NIKKEI225_COMPONENTS を追加済み

### ユースケース

#### 例1: Yahoo ティッカーから判定
```python
async with AsyncSessionLocal() as session:
    matcher = Nikkei225Matcher(session)
    is_in = await matcher.is_nikkei225("7203.T")  # True
```

#### 例2: 銘柄属性を取得
```python
# 日経225判定後、STOCK_MASTER から属性取得
if is_in:
    stmt = select(StockMaster).where(StockMaster.stock_code == "7203")
    stock = (await session.execute(stmt)).scalar_one()
    print(f"銘柄名: {stock.stock_name}")
```

#### 例3: APIから実行
```bash
curl -X POST http://localhost:8000/api/v1/stock-master/fetch
# レスポンスに nikkei225 フィールドが追加される
```

---

## 設計原則（再掲）

✅ **シンプル**: テーブル構造5カラムのみ
✅ **正規化**: 銘柄属性の重複排除
✅ **保守性**: STOCK_MASTER が一元管理
✅ **拡張性**: 履歴トラッキング可能（effective_date）
✅ **自動連携**: STOCK_MASTER更新時に自動実行
✅ **エラー耐性**: 日経225失敗時もSTOCK_MASTERは成功
