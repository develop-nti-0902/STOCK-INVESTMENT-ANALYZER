"""Unit tests (minimal) for balance_sheet saver."""


def test_import_saver():
    """Smoke test: import saver module."""
    import app.services.data_synchronization.market_data.edinet.balance_sheet.saver as m

    assert m is not None
