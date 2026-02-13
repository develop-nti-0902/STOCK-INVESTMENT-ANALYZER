"""Unit tests for EdinetStockDividendParser."""

from __future__ import annotations

from datetime import date

from lxml import etree

from app.services.market_data.edinet.stock_dividend.parser import EdinetStockDividendParser


class _DummyParsed:
    def get_data_by_context_ref(self, tag, ctx):
        # return a dummy object with get_value method
        class V:
            def get_value(self):
                return "12.34"

        return V()


def test_parse_root_extracts_dividend_and_period():
    """XML から配当と期間が正しく抽出されることを検証する."""
    xml = """
    <root xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:jpcrp_cor="http://example.com/jpcrp_cor">
      <xbrli:context id="CurrentYearDuration"><xbrli:endDate>2024-03-31</xbrli:endDate></xbrli:context>
      <jpcrp_cor:CashDividendsPerShare contextRef="CurrentYearDuration">12.34</jpcrp_cor:CashDividendsPerShare>
    </root>
    """

    root = etree.fromstring(xml.encode("utf-8"))
    parser = EdinetStockDividendParser()
    parsed_xbrl = _DummyParsed()

    result = parser.parse_root(root, parsed_xbrl)
    assert "current" in result
    cur = result["current"]
    assert cur is not None
    assert cur.get("dividend_actual") == 12.34 or float(str(cur.get("dividend_actual"))) == 12.34
    # period_end_date should be parsed as date
    assert isinstance(cur.get("period_end_date"), date)
