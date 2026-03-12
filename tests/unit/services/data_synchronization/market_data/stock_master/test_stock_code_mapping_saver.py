"""Unit tests for StockCodeMappingSaver."""


def test_saver_has_required_methods():
    """Test StockCodeMappingSaver has required methods."""
    from app.services.data_synchronization.market_data.stock_master import StockCodeMappingSaver

    assert hasattr(StockCodeMappingSaver, "save_batch")

    class _DummyRepo:
        """Dummy repository for testing."""

        async def bulk_upsert(self, records):
            """Perform bulk upsert."""
            return len(records)

    repo = _DummyRepo()
    saver = StockCodeMappingSaver(repo)
    assert saver.repo == repo
    assert saver.batch_size == 500
