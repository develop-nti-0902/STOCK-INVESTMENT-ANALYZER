"""Unit tests (minimal) for balance_sheet converter."""


def test_import_converter():
    """Smoke test: import converter module."""
    import app.services.data_synchronization.market_data.edinet.balance_sheet.converter as m

    assert m is not None
