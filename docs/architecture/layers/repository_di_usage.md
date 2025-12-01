# Repository依存性注入（DI）使用例

このドキュメントでは、FastAPIのDependsパターンを使用したRepository DIの使用例を示します。

## 概要

`app.api.dependencies.repositories`モジュールは、FastAPIのエンドポイントでRepositoryを簡単に注入するための
依存性プロバイダを提供します。共通モジュール（`app.utils.database`）の`get_db()`を使用してDBセッションを
取得し、各Repositoryインスタンスを作成します。

参照仕様書: `docs/architecture/layers/data_access_layer.md` 3.3章

## 基本的な使用方法

### パターン1: Repositoryを直接注入

最もシンプルな方法です。依存性プロバイダ関数を使用してRepositoryを直接注入します。

```python
from fastapi import APIRouter, Depends
from app.repositories.base import BaseRepository
from app.api.dependencies.repositories import get_base_repository

router = APIRouter()

@router.get("/items/{item_id}")
async def get_item(
    item_id: int,
    repo: BaseRepository = Depends(get_base_repository)
):
    """アイテムをIDで取得"""
    item = await repo.get_by_id(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
```

### パターン2: DBセッションを注入してRepository作成

より柔軟な方法です。DBセッションを直接注入し、エンドポイント内でRepositoryを作成します。

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.utils.database import get_db

router = APIRouter()

@router.get("/items/")
async def list_items(
    db: AsyncSession = Depends(get_db)
):
    """アイテム一覧を取得"""
    repo = BaseRepository(model=Item, session=db)
    items = await repo.get_all(limit=100)
    return {"items": [item.to_dict() for item in items]}
```

## エンティティ専用Repositoryの使用例

将来的に各エンティティ専用のRepository（例: `StockRepository`）が実装された後は、
以下のように使用します。

### 株価データRepository（StockRepository）の例

```python
# app/api/dependencies/repositories.py に追加する依存性プロバイダ
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.stock import StockRepository
from app.models.stock_data import Stocks1d
from app.utils.database import get_db

def get_stock_repository(
    db: AsyncSession = Depends(get_db)
) -> StockRepository:
    """StockRepositoryを提供（株価データ専用）"""
    return StockRepository(model=Stocks1d, session=db)
```

```python
# app/api/v1/stock_data.py での使用例
from fastapi import APIRouter, Depends, HTTPException
from datetime import date
from app.repositories.stock import StockRepository
from app.api.dependencies.repositories import get_stock_repository

router = APIRouter()

@router.get("/stocks/{symbol}")
async def get_stock_data(
    symbol: str,
    start_date: date | None = None,
    end_date: date | None = None,
    repo: StockRepository = Depends(get_stock_repository)
):
    """銘柄コードで株価データを取得"""
    data = await repo.get_by_symbol_range(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        limit=100
    )

    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"Stock data not found for symbol: {symbol}"
        )

    return {
        "symbol": symbol,
        "data": [item.to_dict() for item in data]
    }

@router.post("/stocks/bulk")
async def bulk_upsert_stock_data(
    records: list[dict],
    repo: StockRepository = Depends(get_stock_repository)
):
    """株価データを一括登録・更新"""
    count = await repo.bulk_upsert(records)
    return {
        "message": "Bulk upsert completed",
        "affected_rows": count
    }
```

## 複数のRepositoryを同時に使用する例

複数のRepositoryを組み合わせて使用することもできます。

```python
from fastapi import APIRouter, Depends
from app.repositories.stock import StockRepository
from app.repositories.master import MasterRepository
from app.api.dependencies.repositories import (
    get_stock_repository,
    get_master_repository
)

router = APIRouter()

@router.get("/stocks/{symbol}/with-master")
async def get_stock_with_master(
    symbol: str,
    stock_repo: StockRepository = Depends(get_stock_repository),
    master_repo: MasterRepository = Depends(get_master_repository)
):
    """株価データと銘柄マスタ情報を同時に取得"""
    # 銘柄マスタ情報を取得
    master = await master_repo.get_by_symbol(symbol)
    if master is None:
        raise HTTPException(status_code=404, detail="Stock not found")

    # 株価データを取得
    stock_data = await stock_repo.get_by_symbol_range(
        symbol=symbol,
        limit=30
    )

    return {
        "master": master.to_dict(),
        "recent_data": [item.to_dict() for item in stock_data]
    }
```

## トランザクション管理

`get_db()`は自動的にコミット・ロールバックを行いますが、
明示的にトランザクションを管理したい場合は以下のようにします。

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.database import get_db
from app.repositories.stock import StockRepository

router = APIRouter()

@router.post("/stocks/complex-operation")
async def complex_operation(
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    """複雑なトランザクション処理の例"""
    try:
        # 複数のRepository操作を同一トランザクション内で実行
        stock_repo = StockRepository(model=Stocks1d, session=db)

        # 操作1
        await stock_repo.create(**data["stock"])

        # 操作2
        await stock_repo.bulk_upsert(data["bulk_data"])

        # 全ての操作が成功した場合のみコミット
        # get_db()が自動でコミットするため、明示的なコミットは不要

        return {"message": "Operation completed successfully"}
    except Exception as e:
        # 例外が発生した場合、get_db()が自動でロールバック
        raise HTTPException(status_code=500, detail=str(e))
```

## テスト時のモック注入

テスト時には、依存性プロバイダをオーバーライドしてモックを注入できます。

```python
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from app.main import app
from app.api.dependencies.repositories import get_stock_repository

# モックRepositoryを作成
mock_stock_repo = AsyncMock()
mock_stock_repo.get_by_symbol_range.return_value = [
    # モックデータ
]

# 依存性をオーバーライド
app.dependency_overrides[get_stock_repository] = lambda: mock_stock_repo

# テストクライアントで使用
client = TestClient(app)
response = client.get("/stocks/7203.T")
assert response.status_code == 200
```

## 注意事項

1. **セッションの有効期限**: `get_db()`で提供されるセッションは、リクエストスコープで管理されます。
   エンドポイント関数の外部でセッションを使用しないでください。

2. **トランザクション管理**: `get_db()`は自動的にコミット・ロールバックを行います。
   明示的なコミットは通常不要ですが、複雑なトランザクション処理の場合は適切に管理してください。

3. **Repository作成**: 各エンティティ専用のRepositoryプロバイダを実装する際は、
   適切なモデルクラスとセッションを渡すことを忘れないでください。

## 関連ドキュメント

- データアクセス層仕様書: `docs/architecture/layers/data_access_layer.md`
- Repository基底クラス: `app/repositories/base.py`
- データベース接続管理: `app/utils/database.py`
