"""
StockMasterService単体テスト

銘柄マスタサービス（オーケストレーション層）の機能をテストします。
"""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from app.repositories.stock_master_repository import StockMasterRepository
from app.services.market_data.stock_master.fetcher import StockMasterFetcher
from app.services.market_data.stock_master.service import StockMasterService


class TestStockMasterService:
    """StockMasterServiceのテストクラス"""

    def setup_method(self):
        """テスト前準備"""
        # モックの作成
        self.mock_repo = MagicMock(spec=StockMasterRepository)
        self.mock_fetcher = MagicMock(spec=StockMasterFetcher)

        # Serviceインスタンス作成
        self.service = StockMasterService(
            repo=self.mock_repo,
            fetcher=self.mock_fetcher,
        )

    @pytest.mark.asyncio
    async def test_get_all_active_symbols_success(self):
        """全アクティブ銘柄取得の成功ケース"""
        # テストデータ
        expected_symbols = ["7203", "8306", "9432"]

        # モックの設定
        self.mock_repo.get_all_active_symbols = AsyncMock(
            return_value=expected_symbols
        )

        # テスト実行
        result = await self.service.get_all_active_symbols()

        # 検証
        assert result == expected_symbols
        self.mock_repo.get_all_active_symbols.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_active_symbols_failure(self):
        """全アクティブ銘柄取得の失敗ケース"""
        # モックの設定
        self.mock_repo.get_all_active_symbols = AsyncMock(
            side_effect=Exception("DB error")
        )

        # テスト実行と検証
        with pytest.raises(Exception, match="DB error"):
            await self.service.get_all_active_symbols()

    @pytest.mark.asyncio
    async def test_get_symbols_by_market_success(self):
        """市場別銘柄取得の成功ケース"""
        # テストデータ
        market = "プライム"
        expected_symbols = ["7203", "8306"]

        # モックの設定
        self.mock_repo.get_symbols_by_market = AsyncMock(
            return_value=expected_symbols
        )

        # テスト実行
        result = await self.service.get_symbols_by_market(market)

        # 検証
        assert result == expected_symbols
        self.mock_repo.get_symbols_by_market.assert_called_once_with(market)

    @pytest.mark.asyncio
    async def test_get_symbols_by_market_failure(self):
        """市場別銘柄取得の失敗ケース"""
        # テストデータ
        market = "プライム"

        # モックの設定
        self.mock_repo.get_symbols_by_market = AsyncMock(
            side_effect=Exception("DB error")
        )

        # テスト実行と検証
        with pytest.raises(Exception, match="DB error"):
            await self.service.get_symbols_by_market(market)

    @pytest.mark.asyncio
    async def test_get_symbols_by_sector_success(self):
        """業種別銘柄取得の成功ケース"""
        # テストデータ
        sector = "電気機器"
        expected_symbols = ["7203", "6501"]

        # モックの設定
        self.mock_repo.get_symbols_by_sector = AsyncMock(
            return_value=expected_symbols
        )

        # テスト実行
        result = await self.service.get_symbols_by_sector(sector)

        # 検証
        assert result == expected_symbols
        self.mock_repo.get_symbols_by_sector.assert_called_once_with(sector)

    @pytest.mark.asyncio
    async def test_get_symbols_by_sector_failure(self):
        """業種別銘柄取得の失敗ケース"""
        # テストデータ
        sector = "電気機器"

        # モックの設定
        self.mock_repo.get_symbols_by_sector = AsyncMock(
            side_effect=Exception("DB error")
        )

        # テスト実行と検証
        with pytest.raises(Exception, match="DB error"):
            await self.service.get_symbols_by_sector(sector)

    @pytest.mark.asyncio
    async def test_refresh_stock_master_success(self):
        """銘柄マスタ更新の成功ケース"""

        # Arrange: フェッチャーが2件返し、bulk_upsert が件数を返す
        class FakeModel:
            def __init__(self, symbol: str):
                self._d = {"stock_code": symbol}

            def model_dump(self, *args, **kwargs):
                return self._d

        self.mock_fetcher.fetch_all = AsyncMock(
            return_value=[FakeModel("A"), FakeModel("B")]
        )

        async def fake_bulk(records):
            return len(records)

        self.mock_repo.bulk_upsert = AsyncMock(side_effect=fake_bulk)
        self.mock_repo.get_all_active_symbols = AsyncMock(return_value=[])

        # Act
        result = await self.service.refresh_stock_master()

        # Assert
        assert result == 2

    @pytest.mark.asyncio
    async def test_refresh_stock_master_failure(self):
        """銘柄マスタ更新の失敗ケース"""
        # Arrange: フェッチ時に例外を発生させる
        self.mock_fetcher.fetch_all = AsyncMock(
            side_effect=Exception("Fetch error")
        )
        self.mock_repo.get_all_active_symbols = AsyncMock(return_value=[])

        # Act / Assert
        with pytest.raises(Exception, match="Fetch error"):
            await self.service.refresh_stock_master()


# fetch_and_store 相当の振る舞いは refresh_stock_master に統一されたため、
# テストは refresh_stock_master を呼び出すように更新しています。
@pytest.mark.asyncio
async def test_fetch_and_store_calls_repo_bulk_upsert():
    """fetch_and_storeがリポジトリのbulk_upsertを適切に呼び出すことを確認"""
    # Arrange: モックのフェッチャーが2件返すようにする
    from app.schemas.market_data.stock_master import StockMasterNormalized

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
    processed = await service.refresh_stock_master(batch_size=1)

    # Assert: 2レコード処理されるはず
    assert processed == 2
    # Assert: bulk_upsert は少なくとも1回呼ばれていること
    assert mock_repo.bulk_upsert.called


@pytest.mark.asyncio
async def test_fetch_and_store_fetcher_error_propagates():
    """フェッチャーのエラーが適切に伝搬することを確認"""
    # Arrange
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch_all = AsyncMock(side_effect=RuntimeError("fetch fail"))
    mock_repo = AsyncMock()

    service = StockMasterService(repo=mock_repo, fetcher=mock_fetcher)

    # Act / Assert: フェッチ時の例外が伝搬する
    with pytest.raises(RuntimeError):
        await service.refresh_stock_master()


@pytest.mark.asyncio
async def test_fetch_and_store_repo_error_propagates():
    """リポジトリのエラーが適切に伝搬することを確認"""
    from app.schemas.market_data.stock_master import StockMasterNormalized

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
        await service.refresh_stock_master()


@pytest.mark.asyncio
async def test_fetch_and_store_invalid_item_type_raises():
    """不正な型のアイテムでTypeErrorが発生することを確認"""
    # Arrange: フェッチャーが dict を返す（不正な型）
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch_all = AsyncMock(return_value=[{"code": "1301"}])

    mock_repo = AsyncMock()
    service = StockMasterService(repo=mock_repo, fetcher=mock_fetcher)

    # Act / Assert: Pydantic モデルではないアイテムで TypeError
    with pytest.raises(TypeError):
        await service.refresh_stock_master()


@pytest.mark.asyncio
async def test_refresh_creates_and_updates_summary_success():
    # Arrange
    repo = Mock()
    repo.get_all_active_symbols = AsyncMock(return_value=["A", "B"])
    repo.bulk_upsert = AsyncMock(return_value=2)
    repo.delete_all = AsyncMock(return_value=0)

    updates_repo = Mock()
    # create_summary returns a simple object with id attribute
    created = Mock()
    created.id = 123
    updates_repo.create_summary = AsyncMock(return_value=created)
    updates_repo.update_status = AsyncMock(return_value=None)

    # prepare a fake fetcher that yields Pydantic-like objects
    class FakeModel:
        def __init__(self, symbol: str):
            self._d = {"stock_code": symbol}

        def model_dump(self, *args, **kwargs) -> dict:
            # Pydantic v2 の model_dump 呼び出しを模倣
            return self._d

    fetcher = Mock()
    fetcher.fetch_all = AsyncMock(
        return_value=[FakeModel("A"), FakeModel("C")]
    )

    svc = StockMasterService(
        repo=repo, fetcher=fetcher, updates_repo=updates_repo
    )

    # Act
    processed = await svc.refresh_stock_master()

    # Assert
    assert processed == 2
    updates_repo.create_summary.assert_awaited_once()
    updates_repo.update_status.assert_awaited()
    # final update should be called with status "success"
    called_args = updates_repo.update_status.await_args.args
    assert called_args[1] in ("success",)


@pytest.mark.asyncio
async def test_refresh_marks_failed_on_exception():
    # Arrange
    repo = Mock()
    repo.get_all_active_symbols = AsyncMock(return_value=["A"])
    repo.bulk_upsert = AsyncMock()

    updates_repo = Mock()
    created = Mock()
    created.id = 321
    updates_repo.create_summary = AsyncMock(return_value=created)
    updates_repo.update_status = AsyncMock(return_value=None)

    fetcher = Mock()
    fetcher.fetch_all = AsyncMock(side_effect=RuntimeError("fetch error"))

    svc = StockMasterService(
        repo=repo, fetcher=fetcher, updates_repo=updates_repo
    )

    # Act / Assert
    with pytest.raises(RuntimeError):
        await svc.refresh_stock_master()

    updates_repo.create_summary.assert_awaited_once()
    updates_repo.update_status.assert_awaited()
    # ensure failed status was set
    called_args = updates_repo.update_status.await_args.args
    assert called_args[1] == "failed"


@pytest.mark.asyncio
async def test_reset_deletes_summaries_and_master():
    # Arrange
    repo = Mock()
    repo.delete_all = AsyncMock(return_value=5)

    updates_repo = Mock()
    updates_repo.delete_by_reset = AsyncMock(return_value=3)

    svc = StockMasterService(
        repo=repo, fetcher=None, updates_repo=updates_repo
    )

    # Act
    deleted = await svc.reset_stock_master()

    # Assert
    assert deleted == 5
    updates_repo.delete_by_reset.assert_awaited_once()
