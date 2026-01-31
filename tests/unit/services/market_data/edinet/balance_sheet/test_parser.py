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


def test_parse_returns_five_years():
    root = _make_sample_root()
    p = EdinetBalanceSheetParser()
    out = p.parse(root)
    assert isinstance(out, dict)
    assert set(out.keys()) == set(p.YEARS)
    # current 年の assets は最初の Assets 要素
    assert out["current"]["assets"] == 1000.0
    assert out["current"]["liabilities"] == 400.0
    assert out["current"]["equity"] == 600.0
    assert out["current"]["consolidation"] is True


def test_validate_data():
    root = _make_sample_root()
    p = EdinetBalanceSheetParser()
    assert p.validate_data(root) is True
