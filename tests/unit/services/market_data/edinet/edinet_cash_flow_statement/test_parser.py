"""Tests for EdinetCashFlowStatementParser."""

from __future__ import annotations

from datetime import date

from lxml import etree

from app.services.market_data.edinet.edinet_cash_flow_statement.parser import (
    EdinetCashFlowStatementParser,
)


def _build_sample_root():
    xml = """
<xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:jpcrp_cor="http://example.org/xbrl">
    <xbrli:context id="CurrentYearDuration">
        <xbrli:period>
            <xbrli:startDate>2023-04-01</xbrli:startDate>
            <xbrli:endDate>2024-03-31</xbrli:endDate>
        </xbrli:period>
    </xbrli:context>
    <jpcrp_cor:OperatingCashFlows contextRef="CurrentYearDuration">1000</jpcrp_cor:OperatingCashFlows>
</xbrl>
"""
    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(xml.encode("utf-8"), parser=parser)
    return root


def test_validate_data_and_parse_root():
    """XML ルートの検証とパースの動作を確認する."""
    root = _build_sample_root()
    parser = EdinetCashFlowStatementParser()

    assert parser.validate_data(root)

    class FakeParsed:
        def get_data_by_context_ref(self, tag, ctx):
            class V:
                def get_value(self):
                    return 500

            return V()

    parsed = FakeParsed()
    res = parser.parse_root(root, parsed)

    assert isinstance(res, dict)
    cur = res.get("current")
    assert cur is not None
    assert cur["operating_cf"] == 500 or float(cur["operating_cf"]) == 500.0
    assert cur["period_end_date"] == date(2024, 3, 31)
