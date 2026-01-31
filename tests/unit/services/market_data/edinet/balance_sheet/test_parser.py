from __future__ import annotations

from lxml import etree

from app.services.market_data.edinet.balance_sheet.parser import (
    EdinetBalanceSheetParser,
)


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
    assert set(out.keys()) == set(p.YEARS)
    # コンテキスト情報がないため各年度のデータは None になる
    assert out["current"] is None


def test_validate_data():
    root = _make_sample_root()
    p = EdinetBalanceSheetParser()
    # サンプルには contextRef / context 要素がないため False を返す
    assert p.validate_data(root) is False
