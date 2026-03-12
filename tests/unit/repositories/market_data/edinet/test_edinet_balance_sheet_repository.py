"""Unit tests (minimal) for Edinet balance sheet repository."""


def test_import_edinet_balance_sheet_repository():
    """Smoke test: import repository module."""
    import app.repositories.market_data.edinet.edinet_balance_sheet_repository as m

    assert m is not None
