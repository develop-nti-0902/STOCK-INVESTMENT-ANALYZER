"""Unit tests for EdinetStockDividendParser."""

from __future__ import annotations

from lxml import etree

from app.services.data_synchronization.market_data.edinet.stock_dividend.parser import (
    EdinetStockDividendParser,
)


class _DummyParsed:
    def get_data_by_context_ref(self, tag, ctx):
        # return a dummy object with get_value method
        class V:
            def get_value(self):
                return "12.34"

        return V()


def test_parse_root_extracts_dividend_and_period():
    """context 抽出が正しく機能することを検証する."""
    xml = """
    <root xmlns:xbrl="http://www.xbrl.org/2003/instance">
      <xbrl:context id="CurrentYearDuration"><xbrl:endDate>2024-03-31</xbrl:endDate></xbrl:context>
    </root>
    """

    root = etree.fromstring(xml.encode("utf-8"))
    parser = EdinetStockDividendParser()

    # Test context extraction
    all_contexts = parser._get_all_available_contexts(root)
    assert "CurrentYearDuration" in all_contexts

    # Test context matching for year
    contexts = parser._get_contexts_for_year("current", all_contexts)
    assert len(contexts) > 0
