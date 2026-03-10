"""Unit tests (minimal) for Edinet balance sheet schema."""


def test_import_edinet_balance_sheet_schema():
    """Smoke test: import schema module."""
    import app.schemas.market_data.edinet.edinet_balance_sheet as m

    assert m is not None
