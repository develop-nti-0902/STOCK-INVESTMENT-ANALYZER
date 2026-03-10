"""Unit tests (minimal) for balance_sheet service."""


def test_import_service():
    """Smoke test: import service module."""
    import app.services.data_synchronization.market_data.edinet.balance_sheet.service as m

    assert m is not None
