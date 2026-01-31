from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from lxml import etree

from app.services.core.parsers.base_parser import BaseParser
from app.services.core.parsers.xml_parser_mixin import XMLParserMixin


class EdinetBalanceSheetParser(BaseParser, XMLParserMixin):
    """XBRL から貸借対照表を抽出するパーサー。

    現行年度（current）と過去4年（prior1..prior4）の計5年分を返します。
    実運用では XBRL の名前空間・要素名に合わせて XPath を調整してください。
    """

    YEARS = ["current", "prior1", "prior2", "prior3", "prior4"]

    def parse(self, data: Any) -> Dict[str, Any]:
        root: etree._Element
        if isinstance(data, str):
            root = self.parse_xml(data)
        elif isinstance(data, etree._Element):
            root = data
        else:
            raise TypeError("data must be file path or lxml root element")

        result: Dict[str, Any] = {}
        for idx, year_key in enumerate(self.YEARS):
            result[year_key] = self.parse_single_year(root, idx)
        return result

    def parse_single_year(
        self, root: etree._Element, year_offset: int
    ) -> Dict[str, Any]:
        assets = self.extract_assets(root, year_offset)
        liabilities = self.extract_liabilities(root, year_offset)
        equity = self.extract_equity(root, year_offset)
        period_end = self.get_period_end_date(root, year_offset)
        consolidation = self.determine_consolidation(root, year_offset)
        metrics = self.calculate_metrics(assets, liabilities, equity)

        return {
            "assets": assets,
            "liabilities": liabilities,
            "equity": equity,
            "period_end": period_end,
            "consolidation": consolidation,
            "metrics": metrics,
        }

    def validate_data(self, data: Any) -> bool:
        try:
            root = (
                data
                if isinstance(data, etree._Element)
                else self.parse_xml(data)
            )
        except Exception:
            return False
        # 簡易検証: 少なくとも Assets, Liabilities, Equity のいずれかが存在すること
        for name in ("Assets", "Liabilities", "Equity"):
            nodes = root.xpath(f".//*[local-name() = '{name}']")
            if nodes:
                return True
        return False

    def extract_assets(
        self, root: etree._Element, year_offset: int
    ) -> Optional[float]:
        return self._extract_numeric_by_localname(root, "Assets", year_offset)

    def extract_liabilities(
        self, root: etree._Element, year_offset: int
    ) -> Optional[float]:
        return self._extract_numeric_by_localname(
            root, "Liabilities", year_offset
        )

    def extract_equity(
        self, root: etree._Element, year_offset: int
    ) -> Optional[float]:
        return self._extract_numeric_by_localname(root, "Equity", year_offset)

    def calculate_metrics(
        self,
        assets: Optional[float],
        liabilities: Optional[float],
        equity: Optional[float],
    ) -> Dict[str, Optional[float]]:
        assets_val = assets or 0.0
        liabilities_val = liabilities or 0.0
        equity_val = equity or 0.0
        return {
            "working_capital": (
                None
                if assets is None or liabilities is None
                else assets_val - liabilities_val
            ),
            "equity_ratio": (
                None if assets_val == 0 else (equity_val / assets_val)
            ),
            "net_assets": equity_val,
        }

    def determine_consolidation(
        self, root: etree._Element, year_offset: int
    ) -> Optional[bool]:
        # XBRL に Consolidated 要素がある場合はそれを解釈する（true/false）
        nodes = root.xpath(".//*[local-name() = 'Consolidated']")
        if not nodes:
            return None
        text = (nodes[0].text or "").strip().lower()
        if text in ("true", "1", "yes"):
            return True
        if text in ("false", "0", "no"):
            return False
        return None

    def get_period_end_date(
        self, root: etree._Element, year_offset: int
    ) -> Optional[str]:
        nodes = root.xpath(".//*[local-name() = 'PeriodEndDate']")
        if nodes and nodes[0].text:
            try:
                dt = datetime.fromisoformat(nodes[0].text.strip())
                return dt.date().isoformat()
            except Exception:
                return nodes[0].text.strip()
        # フォールバック: 要素の period 属性を探す
        nodes = root.xpath(".//*[@period]")
        if nodes:
            val = nodes[0].get("period")
            return val
        return None

    def _extract_numeric_by_localname(
        self, root: etree._Element, localname: str, year_offset: int
    ) -> Optional[float]:
        # 単純化のため、同名要素を年順で拾い、offset 番目を返す
        nodes = root.xpath(f".//*[local-name() = '{localname}']")
        if len(nodes) <= year_offset:
            return None
        text = (nodes[year_offset].text or "").strip()
        try:
            return float(text.replace(",", "")) if text else None
        except Exception:
            return None
