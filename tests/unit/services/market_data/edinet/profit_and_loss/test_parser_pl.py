"""EDINET 損益・キャッシュフローパーサのユニットテストモジュール（profit_and_loss 固有）。

主にコンテキスト抽出、期間解析、財務指標の数値抽出等を検証します。
"""

from __future__ import annotations

import pytest
from lxml import etree

from app.services.market_data.edinet.profit_and_loss.parser import EdinetProfitAndLossParser


def _make_sample_root() -> etree._Element:
    xml = """
    <Document xmlns:xbrli="http://www.xbrl.org/2003/instance"
              xmlns:jpcrp_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2024-12-31/jpcrp_cor"
              xmlns:jppfs_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2024-12-31/jppfs_cor">
      <xbrli:context id="CurrentYearDuration">
        <xbrli:period>
          <xbrli:startDate>2024-04-01</xbrli:startDate>
          <xbrli:endDate>2025-03-31</xbrli:endDate>
        </xbrli:period>
      </xbrli:context>
      <jpcrp_cor:BasicEarningsLossPerShareSummaryOfBusinessResults contextRef="CurrentYearDuration">120.5</jpcrp_cor:BasicEarningsLossPerShareSummaryOfBusinessResults>
      <jppfs_cor:NetCashProvidedByUsedInOperatingActivities contextRef="CurrentYearDuration">1500.0</jppfs_cor:NetCashProvidedByUsedInOperatingActivities>
    </Document>
    """
    return etree.fromstring(xml.encode("utf-8"))


def test_parse_returns_five_years(monkeypatch):
    root = _make_sample_root()

    class _DummyParsedXbrl:
        def get_data_by_context_ref(self, ctx):
            return []

    class _DummyXbrlParser:
        def parse_file(self, _path):
            return _DummyParsedXbrl()

    import app.services.market_data.edinet.profit_and_loss.parser as pl_parser

    monkeypatch.setattr(pl_parser, "XbrlParser", _DummyXbrlParser)

    p = EdinetProfitAndLossParser()
    p.parse_xml = lambda _: root
    result = p.parse("/tmp/dummy.xbrl")

    expected_keys = ["current", "prior1", "prior2", "prior3", "prior4"]
    assert set(result.keys()) == set(expected_keys)


def test_single_year_parse_basic():
    root = _make_sample_root()
    contexts = ["CurrentYearDuration"]

    class _DummyParsedXbrl:
        def get_data_by_context_ref(self, ctx):
            return []

    p = EdinetProfitAndLossParser()
    parsed_xbrl = _DummyParsedXbrl()

    result = p.parse_single_year(parsed_xbrl, root, contexts, "current")

    assert result is not None
    # フォーマットは balance_sheet に合わせた年別辞書形式（eps, operating_profit, period_end, consolidation）
    assert "eps" in result
    assert "operating_profit" in result
    assert "period_end" in result
    assert "consolidation" in result


def test_get_all_available_contexts():
    xml = """
    <Document>
      <Element1 contextRef="CurrentYearDuration"/>
      <Element2 contextRef="Prior1YearDuration"/>
      <Element3 contextRef="CurrentYearDuration"/>
      <Element4/>
    </Document>
    """
    root = etree.fromstring(xml.encode("utf-8"))

    p = EdinetProfitAndLossParser()
    contexts = p._get_all_available_contexts(root)

    assert "CurrentYearDuration" in contexts
    assert "Prior1YearDuration" in contexts
    assert len(contexts) == 2


def test_get_contexts_for_year():
    all_contexts = [
        "CurrentYearDuration",
        "CurrentYearDuration_ConsolidatedMember",
        "Prior1YearDuration",
        "SomeOtherContext",
    ]

    p = EdinetProfitAndLossParser()

    current_contexts = p._get_contexts_for_year("current", all_contexts)
    assert "CurrentYearDuration" in current_contexts
    assert "CurrentYearDuration_ConsolidatedMember" in current_contexts
    assert len(current_contexts) >= 1

    prior1_contexts = p._get_contexts_for_year("prior1", all_contexts)
    assert "Prior1YearDuration" in prior1_contexts


def test_extract_value_with_context_no_match():
    root = _make_sample_root()

    class _DummyParsedXbrl:
        def get_data_by_context_ref(self, ctx):
            return []

    p = EdinetProfitAndLossParser()
    parsed_xbrl = _DummyParsedXbrl()

    # 新 API: 単純抽出は `extract_numeric_from_xbrl` を使う
    value = p.extract_numeric_from_xbrl(parsed_xbrl, ["NonExistentTag"], ["NonExistentContext"])
    assert value is None


def test_extract_period_end_date():
    xml = """
    <Document xmlns:xbrli="http://www.xbrl.org/2003/instance">
      <xbrli:context id="CurrentYearDuration">
        <xbrli:period>
          <xbrli:startDate>2024-04-01</xbrli:startDate>
          <xbrli:endDate>2025-03-31</xbrli:endDate>
        </xbrli:period>
      </xbrli:context>
    </Document>
    """
    root = etree.fromstring(xml.encode("utf-8"))
    contexts = ["CurrentYearDuration"]

    p = EdinetProfitAndLossParser()
    date_result = p.get_period_end_date(root, contexts)

    assert date_result is not None
    assert str(date_result) == "2025-03-31"


def test_extract_period_end_date_no_context():
    root = _make_sample_root()
    contexts = ["NonExistentContext"]

    p = EdinetProfitAndLossParser()
    date_result = p.get_period_end_date(root, contexts)

    assert date_result is None
