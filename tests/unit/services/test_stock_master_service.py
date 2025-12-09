"""StockMasterService の単体テスト

各テストは AAA パターン（Arrange / Act / Assert）に従って記述します。
コメントは日本語で記載しています。
"""

from unittest.mock import AsyncMock

import pytest

from app.schemas.market_data.stock_master import StockMasterNormalized
from app.services.market_data.stock_master.service import StockMasterService


@pytest.mark.asyncio
async def test_fetch_and_store_calls_repo_bulk_upsert():
    # Arrange: モックのフェッチャーが2件返すようにする
    mock_item_1 = StockMasterNormalized(
        stock_code="1301",
        stock_name="Test Co",
        market_category="Prime",
    )
    mock_item_2 = StockMasterNormalized(
        stock_code="1332",
        stock_name="Test2 Co",
        market_category="Prime",
    )

    # Arrange
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch_all = AsyncMock(return_value=[mock_item_1, mock_item_2])

    mock_repo = AsyncMock()

    # Arrange: bulk_upsert は受け取った件数を返すように設定
    async def fake_bulk_upsert(records):
        return len(records)

    mock_repo.bulk_upsert = AsyncMock(side_effect=fake_bulk_upsert)

    service = StockMasterService(repo=mock_repo, fetcher=mock_fetcher)

    # Act: 実行
    processed = await service.fetch_and_store("jpx", batch_size=1)

    # Assert: 2レコード処理されるはず
    assert processed == 2
    # Assert: bulk_upsert は 2 回（バッチサイズ1で2回）呼ばれている
    assert mock_repo.bulk_upsert.call_count == 2


@pytest.mark.asyncio
async def test_fetch_and_store_unsupported_source_raises():
    # Arrange
    mock_repo = AsyncMock()
    service = StockMasterService(repo=mock_repo, fetcher=AsyncMock())

    # Act / Assert: 未対応のソース名で ValueError が発生する
    with pytest.raises(ValueError):
        await service.fetch_and_store("unsupported")


@pytest.mark.asyncio
async def test_fetch_and_store_fetcher_error_propagates():
    # Arrange
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch_all = AsyncMock(side_effect=RuntimeError("fetch fail"))
    mock_repo = AsyncMock()

    service = StockMasterService(repo=mock_repo, fetcher=mock_fetcher)

    # Act / Assert: フェッチ時の例外が伝搬する
    with pytest.raises(RuntimeError):
        await service.fetch_and_store("jpx")


@pytest.mark.asyncio
async def test_fetch_and_store_repo_error_propagates():
    # valid pydantic items
    item = StockMasterNormalized(
        stock_code="1301",
        stock_name="Test Co",
    )
    # Arrange
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch_all = AsyncMock(return_value=[item])

    mock_repo = AsyncMock()
    mock_repo.bulk_upsert = AsyncMock(side_effect=RuntimeError("db error"))

    service = StockMasterService(repo=mock_repo, fetcher=mock_fetcher)

    # Act / Assert: リポジトリ側の例外が伝搬する
    with pytest.raises(RuntimeError):
        await service.fetch_and_store("jpx")


@pytest.mark.asyncio
async def test_fetch_and_store_invalid_item_type_raises():
    # Arrange: フェッチャーが dict を返す（不正な型）
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch_all = AsyncMock(return_value=[{"code": "1301"}])

    mock_repo = AsyncMock()
    service = StockMasterService(repo=mock_repo, fetcher=mock_fetcher)

    # Act / Assert: Pydantic モデルではないアイテムで TypeError
    with pytest.raises(TypeError):
        await service.fetch_and_store("jpx")
