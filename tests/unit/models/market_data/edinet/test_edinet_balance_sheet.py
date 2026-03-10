"""Unit tests (minimal) for Edinet balance sheet model."""


def test_import_edinet_balance_sheet():
    """Smoke test: import module."""
    import app.models.market_data.edinet.edinet_balance_sheet as m

    assert m is not None
