"""Unit tests (minimal) for balance_sheet parser."""


def test_import_parser():
    """Smoke test: import parser module."""
    import app.services.data_synchronization.market_data.edinet.balance_sheet.parser as m

    assert m is not None
