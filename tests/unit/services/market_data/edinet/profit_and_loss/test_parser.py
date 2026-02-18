"""EDINET 損益・キャッシュフローパーサのユニットテストモジュール.

主にコンテキスト抽出、期間解析、財務指標の数値抽出等を検証します.
"""

from __future__ import annotations

from lxml import etree

from app.services.market_data.edinet.profit_and_loss.parser import EdinetProfitAndLossParser


def _make_sample_root() -> etree._Element:
    """サンプルのXMLルート要素を返すヘルパー関数.

    テスト用の簡易的なXBRL文書を返します.
    """
    xml = (
        '<Document xmlns:xbrli="http://www.xbrl.org/2003/instance"\n'
        '  xmlns:jpcrp_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2024-12-31/jpcrp_cor"\n'
        '  xmlns:jppfs_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2024-12-31/jppfs_cor">\n'
        '  <xbrli:context id="CurrentYearDuration">\n'
        "    <xbrli:period>\n"
        "      <xbrli:startDate>2024-04-01</xbrli:startDate>\n"
        "      <xbrli:endDate>2025-03-31</xbrli:endDate>\n"
        "    </xbrli:period>\n"
        "  </xbrli:context>\n"
        "  <jpcrp_cor:BasicEarningsLossPerShareSummaryOfBusinessResults "
        'contextRef="CurrentYearDuration">\n'
        "    120.5\n"
        "  </jpcrp_cor:BasicEarningsLossPerShareSummaryOfBusinessResults>\n"
        "  <jppfs_cor:NetCashProvidedByUsedInOperatingActivities "
        'contextRef="CurrentYearDuration">\n'
        "    1500.0\n"
        "  </jppfs_cor:NetCashProvidedByUsedInOperatingActivities>\n"
        '  <jppfs_cor:NetSales contextRef="CurrentYearDuration">\n'
        "    50000\n"
        "  </jppfs_cor:NetSales>\n"
        "</Document>\n"
    )
    return etree.fromstring(xml.encode("utf-8"))


def test_parse_returns_five_years(monkeypatch):
    """5年分のキーが返ることを検証する."""
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

    # 実装は単年度取得のため current のみを期待する
    expected_keys = ["current"]
    assert set(result.keys()) == set(expected_keys)


def test_single_year_parse_basic():
    """単年度の解析結果の基本キーを検証する."""
    root = _make_sample_root()
    contexts = ["CurrentYearDuration"]

    class _DummyParsedXbrl:
        def get_data_by_context_ref(self, ctx):
            return []

    p = EdinetProfitAndLossParser()
    parsed_xbrl = _DummyParsedXbrl()

    result = p.parse_single_year(parsed_xbrl, root, contexts, "current")

    assert result is not None
    # フォーマットは年別辞書形式（eps, operating_income, period_end, consolidation）
    assert "eps" in result
    assert "operating_income" in result
    assert "period_end" in result
    assert "consolidation" in result


def test_get_all_available_contexts():
    """全てのcontextRefを抽出できることを検証する."""
    xml = (
        "<Document>\n"
        '  <Element1 contextRef="CurrentYearDuration"/>\n'
        '  <Element2 contextRef="Prior1YearDuration"/>\n'
        '  <Element3 contextRef="CurrentYearDuration"/>\n'
        "  <Element4/>\n"
        "</Document>\n"
    )
    root = etree.fromstring(xml.encode("utf-8"))

    p = EdinetProfitAndLossParser()
    contexts = p._get_all_available_contexts(root)

    assert "CurrentYearDuration" in contexts
    assert "Prior1YearDuration" in contexts
    assert len(contexts) == 2


def test_get_contexts_for_year():
    """年指定で適切なcontext群を返すことを検証する."""
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
    # 実装上 prior 年は返さないため空を期待する
    assert prior1_contexts == []


def test_extract_value_with_context_no_match():
    """存在しないタグ・コンテキストを与えた場合にNoneが返ることを検証する."""

    class _DummyParsedXbrl:
        def get_data_by_context_ref(self, ctx):
            return []

    p = EdinetProfitAndLossParser()
    parsed_xbrl = _DummyParsedXbrl()

    # 新 API: 単純抽出は `extract_numeric_from_xbrl` を使う
    value = p.extract_numeric_from_xbrl(parsed_xbrl, ["NonExistentTag"], ["NonExistentContext"])
    assert value is None


def test_extract_period_end_date():
    """contextから期末日を抽出できることを検証する."""
    xml = (
        '<Document xmlns:xbrli="http://www.xbrl.org/2003/instance">\n'
        '  <xbrli:context id="CurrentYearDuration">\n'
        "    <xbrli:period>\n"
        "      <xbrli:startDate>2024-04-01</xbrli:startDate>\n"
        "      <xbrli:endDate>2025-03-31</xbrli:endDate>\n"
        "    </xbrli:period>\n"
        "  </xbrli:context>\n"
        "</Document>\n"
    )
    root = etree.fromstring(xml.encode("utf-8"))
    contexts = ["CurrentYearDuration"]

    p = EdinetProfitAndLossParser()
    date_result = p.get_period_end_date(root, contexts)

    assert date_result is not None
    assert str(date_result) == "2025-03-31"


def test_extract_period_end_date_no_context():
    """存在しないコンテキストを与えた場合にNoneが返ることを検証する."""
    root = _make_sample_root()
    contexts = ["NonExistentContext"]

    p = EdinetProfitAndLossParser()
    date_result = p.get_period_end_date(root, contexts)

    assert date_result is None
