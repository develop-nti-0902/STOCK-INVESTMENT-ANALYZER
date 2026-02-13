"""`StockMasterService` の単体テストを新しく作り直しました.

テスト規約に沿い、日本語コメントと非同期テスト用の `pytest.mark.asyncio` を利用しています.
"""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from app.services.market_data.stock_master.service import StockMasterService


class FakeModel:
    """簡易な Pydantic v2 互換オブジェクト（model_dump を持つ）."""

    def __init__(self, code: str):
        """初期化: テスト用の辞書を内部に保持する.

        Args:
            code: 銘柄コード文字列
        """
        self._d = {"stock_code": code}

    def model_dump(self, *args, **kwargs) -> dict:
        """Pydantic v2 の `model_dump` 互換の振る舞いを模す簡易実装.

        Returns:
            内部辞書のコピー.
        """
        return self._d


@pytest.mark.asyncio
async def test_get_all_active_symbols_success_and_error():
    """全件取得が成功するケースと例外が透過されるケースを確認する."""
    mock_repo = MagicMock()
    mock_repo.get_all_active_symbols = AsyncMock(return_value=["7203"])

    svc = StockMasterService(repo=mock_repo, fetcher=None)
    result = await svc.get_all_active_symbols()
    assert result == ["7203"]

    # 例外が透過されること
    mock_repo.get_all_active_symbols = AsyncMock(side_effect=RuntimeError("db"))
    with pytest.raises(RuntimeError):
        await svc.get_all_active_symbols()


@pytest.mark.asyncio
async def test_get_symbols_by_market_and_sector_success_and_error():
    """市場・業種別取得の正常系と例外伝搬を確認する."""
    mock_repo = MagicMock()
    mock_repo.get_symbols_by_market = AsyncMock(return_value=["1111"])
    mock_repo.get_symbols_by_sector = AsyncMock(return_value=["2222"])

    svc = StockMasterService(repo=mock_repo, fetcher=None)

    assert await svc.get_symbols_by_market("Prime") == ["1111"]
    assert await svc.get_symbols_by_sector("Tech") == ["2222"]

    mock_repo.get_symbols_by_market = AsyncMock(side_effect=RuntimeError("mkt err"))
    with pytest.raises(RuntimeError):
        await svc.get_symbols_by_market("Prime")

    mock_repo.get_symbols_by_sector = AsyncMock(side_effect=RuntimeError("sec err"))
    with pytest.raises(RuntimeError):
        await svc.get_symbols_by_sector("Tech")


@pytest.mark.asyncio
async def test_fetch_and_save_uses_converter_and_saver_and_returns_count():
    """fetcher -> converter -> saver の流れで処理件数を返すことを確認する."""
    # Arrange
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch_all = AsyncMock(return_value=[FakeModel("A"), FakeModel("B")])

    mock_converter = MagicMock()
    records = [{"stock_code": "A"}, {"stock_code": "B"}]
    mock_converter.to_records = MagicMock(return_value=records)

    mock_saver = MagicMock()
    mock_saver.save_batch = AsyncMock(return_value=2)

    mock_repo = MagicMock()

    svc = StockMasterService(
        repo=mock_repo, fetcher=mock_fetcher, converter=mock_converter, saver=mock_saver
    )

    # Act
    processed = await svc.fetch_and_save()

    # Assert
    assert processed == 2
    mock_converter.to_records.assert_called_once()
    mock_saver.save_batch.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_and_save_with_updates_repo_marks_success():
    """updates_repo が与えられた場合、サマリが作成され success に更新されることを確認する."""
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch_all = AsyncMock(return_value=[FakeModel("X")])

    mock_converter = MagicMock()
    mock_converter.to_records = MagicMock(return_value=[{"stock_code": "X"}])

    mock_saver = MagicMock()
    mock_saver.save_batch = AsyncMock(return_value=1)

    mock_repo = MagicMock()
    mock_repo.get_all_active_symbols = AsyncMock(return_value=["OLD"])

    updates_repo = MagicMock()
    created = Mock()
    created.id = 999
    updates_repo.create_summary = AsyncMock(return_value=created)
    updates_repo.update_status = AsyncMock()

    svc = StockMasterService(
        repo=mock_repo,
        fetcher=mock_fetcher,
        converter=mock_converter,
        saver=mock_saver,
        updates_repo=updates_repo,
    )

    processed = await svc.fetch_and_save()

    assert processed == 1
    updates_repo.create_summary.assert_awaited_once()
    updates_repo.update_status.assert_awaited()


@pytest.mark.asyncio
async def test_fetch_and_save_invalid_limit_raises_value_error():
    """limit に負の値を与えるとエラーになることを確認する."""
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch_all = AsyncMock(return_value=[FakeModel("Z")])
    svc = StockMasterService(repo=MagicMock(), fetcher=mock_fetcher)

    with pytest.raises(ValueError):
        await svc.fetch_and_save(limit=-1)


@pytest.mark.asyncio
async def test_fetch_and_save_invalid_item_type_raises_type_error():
    """フェッチャーが dict を返した場合 TypeError が発生することを確認する."""
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch_all = AsyncMock(return_value=[{"code": "1301"}])
    svc = StockMasterService(repo=MagicMock(), fetcher=mock_fetcher)

    with pytest.raises(TypeError):
        await svc.fetch_and_save()


@pytest.mark.asyncio
async def test_reset_stock_master_deletes_and_calls_updates_repo():
    """reset_stock_master がリポジトリ削除を行い、updates_repo の削除も呼ぶことを確認する."""
    mock_repo = MagicMock()
    mock_repo.delete_all = AsyncMock(return_value=7)

    updates_repo = MagicMock()
    updates_repo.delete_by_reset = AsyncMock(return_value=3)

    svc = StockMasterService(repo=mock_repo, fetcher=None, updates_repo=updates_repo)
    deleted = await svc.reset_stock_master()

    assert deleted == 7
    updates_repo.delete_by_reset.assert_awaited_once()
