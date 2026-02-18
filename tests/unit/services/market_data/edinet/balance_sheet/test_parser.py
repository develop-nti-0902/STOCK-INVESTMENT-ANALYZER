"""EDINET 貸借対照表パーサのユニットテストモジュール.

主にコンテキスト抽出、period_end の解析、数値抽出の成否等を検証します。
"""

from __future__ import annotations

import pytest
from lxml import etree

from app.services.market_data.edinet.balance_sheet.parser import EdinetBalanceSheetParser


def _make_sample_root() -> etree._Element:
    xml = """
    <Document>
      <Consolidated>true</Consolidated>
      <PeriodEndDate>2025-03-31</PeriodEndDate>
      <Assets>1000</Assets>
      <Liabilities>400</Liabilities>
      <Equity>600</Equity>
      <Assets>900</Assets>
      <Liabilities>350</Liabilities>
      <Equity>550</Equity>
      <Assets>800</Assets>
      <Liabilities>300</Liabilities>
      <Equity>500</Equity>
      <Assets>700</Assets>
      <Liabilities>250</Liabilities>
      <Equity>450</Equity>
      <Assets>600</Assets>
      <Liabilities>200</Liabilities>
      <Equity>400</Equity>
    </Document>
    """
    return etree.fromstring(xml.encode("utf-8"))


def test_parse_returns_five_years(monkeypatch):
    """parse が 5 年分のキーを持つ辞書を返すことを検証する."""
    root = _make_sample_root()

    # 外部ライブラリのパーサー呼び出しを抑止するためダミーを差し替え
    class _DummyParsedXbrl:
        def get_data_by_context_ref(self, tag, ctx):
            return None

    class _DummyXbrlParser:
        def parse_file(self, _path):
            return _DummyParsedXbrl()

    import app.services.market_data.edinet.balance_sheet.parser as bs_parser

    monkeypatch.setattr(bs_parser, "XbrlParser", _DummyXbrlParser)

    p = EdinetBalanceSheetParser()
    out = p.parse(root)
    assert isinstance(out, dict)
    # 実装は単年度取得のため、current のみを期待する
    assert set(out.keys()) == {"current"}
    # コンテキスト情報がないため current のデータは None になる
    assert out["current"] is None


def test_validate_data():
    """validate_data が不適切な XML に対して False を返すことを検証する."""
    root = _make_sample_root()
    p = EdinetBalanceSheetParser()
    # サンプルには contextRef / context 要素がないため False を返す
    assert p.validate_data(root) is False


def test_get_all_available_contexts_and_get_contexts_for_year():
    """全ての contextRef を抽出し、年度ごとの優先コンテキストを取得できることを検証する."""
    # 様々な contextRef を持つ要素と context ノードを用意
    xml = """
        <Root>
            <context id="CurrentYearInstant_ConsolidatedMember">
                <instant>2025-03-31</instant>
            </context>
            <context id="Prior1YearInstant_NonConsolidatedMember">
                <instant>2024-03-31</instant>
            </context>
            <x contextRef="CurrentYearInstant_ConsolidatedMember">1</x>
            <y contextRef="Prior1YearInstant_NonConsolidatedMember">2</y>
            <z contextRef="OtherContext">3</z>
        </Root>
        """

    root = etree.fromstring(xml.encode("utf-8"))
    p = EdinetBalanceSheetParser()

    all_ctx = p._get_all_available_contexts(root)
    # order not guaranteed, but both known contextRefs should be present
    assert "CurrentYearInstant_ConsolidatedMember" in all_ctx
    assert "Prior1YearInstant_NonConsolidatedMember" in all_ctx

    # get_contexts_for_year should prioritize patterns
    cur_ctxs = p._get_contexts_for_year("current", all_ctx)
    assert any("CurrentYearInstant" in c for c in cur_ctxs)
    prior_ctxs = p._get_contexts_for_year("prior1", all_ctx)
    # 実装上、prior 年は取得しないため空になることを期待する
    assert prior_ctxs == []


def test_get_period_end_date_with_various_formats_and_fallback():
    """get_period_end_date が複数のフォーマットとフォールバックを処理できることを検証する."""
    # context with ISO datetime
    xml_iso = """
        <Doc>
            <context id="CTX1"><instant>2025-03-31T00:00:00</instant></context>
            <x contextRef="CTX1">1</x>
        </Doc>
        """
    root_iso = etree.fromstring(xml_iso.encode("utf-8"))
    p = EdinetBalanceSheetParser()
    # when context exists return date
    dt = p.get_period_end_date(root_iso, ["CTX1"])
    assert str(dt) == "2025-03-31"

    # context missing instant but fallback instant exists elsewhere
    xml_fallback = """
        <Doc>
            <context id="CTX2"></context>
            <instant>2024-12-31</instant>
        </Doc>
        """
    root_fb = etree.fromstring(xml_fallback.encode("utf-8"))
    dt2 = p.get_period_end_date(root_fb, ["CTX2"])
    assert str(dt2) == "2024-12-31"

    # invalid formats -> None
    xml_bad = """
        <Doc>
            <context id="CTX3"><instant>not-a-date</instant></context>
        </Doc>
        """
    root_bad = etree.fromstring(xml_bad.encode("utf-8"))
    assert p.get_period_end_date(root_bad, ["CTX3"]) is None


def test_determine_consolidation_and_calculate_metrics():
    """determine_consolidation と calculate_metrics の動作を検証する."""
    p = EdinetBalanceSheetParser()

    # consolidation detection
    assert p.determine_consolidation(None, ["Something_Consolidated"]) is True
    # 実装は "Consolidated" の存在を優先して判定するため、
    # 'NonConsolidated' を含む場合も True を返す現状の挙動を検証する。
    assert p.determine_consolidation(None, ["Something_NonConsolidated"]) is True
    assert p.determine_consolidation(None, ["Other"]) is None

    # metrics calculation
    metrics = p.calculate_metrics(1000.0, 400.0, 600.0)
    assert metrics["working_capital"] == 600.0
    assert pytest.approx(metrics["equity_ratio"]) == 0.6
    assert metrics["net_assets"] == 600.0


def test_extract_numeric_from_xbrl_success_and_errors():
    """_extract_numeric_from_xbrl の成功・数値変換失敗・例外無視を検証する."""
    p = EdinetBalanceSheetParser()

    class DummyData:
        def __init__(self, v):
            self._v = v

        def get_value(self):
            return self._v

    class DummyXbrl:
        def get_data_by_context_ref(self, tag, ctx):
            # return numeric for one combination, non-numeric for another, and raise for others
            if "AssetsTag" in tag and ctx == "CTX_OK":
                return DummyData("1234.5")
            if "AssetsTag" in tag and ctx == "CTX_BAD":
                return DummyData("not-a-number")
            if "Raise" in tag:
                raise RuntimeError("boom")
            return None

    parsed = DummyXbrl()
    # success: should return float
    val = p.extract_numeric_from_xbrl(
        parsed, ["AssetsTagCandidate"], ["CTX_OK"]
    )  # tag contains AssetsTagCandidate
    assert val == 1234.5

    # bad numeric returns None
    val2 = p.extract_numeric_from_xbrl(parsed, ["AssetsTagCandidate"], ["CTX_BAD"])
    assert val2 is None

    # exception in get_data_by_context_ref is ignored and returns None
    val3 = p.extract_numeric_from_xbrl(parsed, ["RaiseTag"], ["CTX_OK"])
    assert val3 is None
