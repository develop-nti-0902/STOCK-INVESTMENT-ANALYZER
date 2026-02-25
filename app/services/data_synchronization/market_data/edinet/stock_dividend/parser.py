"""EDINET の XBRL から配当情報を抽出するパーサーモジュール.

主に `dividend_actual` を抽出することを目的とします。タグ名は候補リストを持ち、
外部の XBRL ヘルパー（edinet_xbrl）を利用して値を取得します。
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from lxml import etree

from app.services.data_synchronization._core.parsers.base_parser import BaseParser
from app.services.data_synchronization._core.parsers.xml_parser_mixin import XMLParserMixin

# Module-level placeholder for external XBRL parser class; tests may monkeypatch this.
XbrlParser = None


class EdinetStockDividendParser(BaseParser, XMLParserMixin):
    """XBRL から配当情報を抽出するパーサー."""

    # 年度キーを profit_and_loss と揃える（将来の拡張性のため）
    YEARS = ["current"]
    # YEARS = ["current", "prior1", "prior2", "prior3", "prior4"]

    # コンテキスト候補パターン（balance_sheet / profit_and_loss と互換性を持たせる）
    CONTEXT_PATTERNS = {
        "current": [
            "CurrentYearDuration",
            "CurrentYearDuration_ConsolidatedMember",
            "CurrentYearDuration_NonConsolidatedMember",
        ],
    }
    # CONTEXT_PATTERNS = {
    #     "current": [
    #         "CurrentYearDuration",
    #         "CurrentYearDuration_ConsolidatedMember",
    #         "CurrentYearDuration_NonConsolidatedMember",
    #     ],
    #     "prior1": [
    #         "Prior1YearDuration",
    #         "Prior1YearDuration_ConsolidatedMember",
    #         "Prior1YearDuration_NonConsolidatedMember",
    #     ],
    #     "prior2": [
    #         "Prior2YearDuration",
    #         "Prior2YearDuration_ConsolidatedMember",
    #         "Prior2YearDuration_NonConsolidatedMember",
    #     ],
    #     "prior3": [
    #         "Prior3YearDuration",
    #         "Prior3YearDuration_ConsolidatedMember",
    #         "Prior3YearDuration_NonConsolidatedMember",
    #     ],
    #     "prior4": [
    #         "Prior4YearDuration",
    #         "Prior4YearDuration_ConsolidatedMember",
    #         "Prior4YearDuration_NonConsolidatedMember",
    #     ],
    # }

    # 配当金を示す XBRL タグ候補（代表的な候補を列挙）
    XBRL_TAGS = {
        "dividend_actual": [
            "jpcrp_cor:DividendPaidPerShareSummaryOfBusinessResults",
        ]
    }

    def parse_root(self, root: etree._Element, parsed_xbrl: Any) -> Dict[str, Any]:
        """Parse the root XML element and extract dividend data for configured years."""
        all_contexts = self._get_all_available_contexts(root)
        result: Dict[str, Any] = {}
        for year_key in self.YEARS:
            contexts = self._get_contexts_for_year(year_key, all_contexts)
            if contexts:
                result[year_key] = self.parse_single_year(parsed_xbrl, root, contexts, year_key)
            else:
                result[year_key] = None
        return result

    def validate_data(self, data: Any) -> bool:
        """Validate input is a file path or an XML element usable by the parser."""
        if data is None:
            return False
        if isinstance(data, (str, Path)):
            if isinstance(data, str):
                path = Path(data)
            else:
                path = data
            return path.exists() and path.is_file()
        from lxml import etree

        if isinstance(data, etree._Element):
            return True
        return False

    def _get_all_available_contexts(self, root: etree._Element) -> List[str]:
        """Return all context IDs from the root element."""
        namespaces = {
            "xbrl": "http://www.xbrl.org/2003/instance",
        }
        context_elements = root.findall(".//xbrl:context", namespaces=namespaces)
        return [elem.get("id") for elem in context_elements if elem.get("id")]

    def _get_contexts_for_year(self, year_key: str, all_contexts: List[str]) -> List[str]:
        """Return matching context IDs for a given year key."""
        if year_key not in self.CONTEXT_PATTERNS:
            return []
        patterns = self.CONTEXT_PATTERNS[year_key]
        matching = []
        for ctx_id in all_contexts:
            for pattern in patterns:
                if pattern in ctx_id:
                    matching.append(ctx_id)
                    break
        return matching

    def parse_single_year(
        self, parsed_xbrl: Any, root: etree._Element, contexts: List[str], year_key: str
    ) -> Dict[str, Any]:
        """Parse data for a single year."""
        result = {}
        for tag_key, tag_list in self.XBRL_TAGS.items():
            for tag_name in tag_list:
                value = self._extract_value(root, tag_name, contexts)
                if value is not None:
                    result[tag_key] = value
                    break
        return result

    def _extract_value(self, root: etree._Element, tag_name: str, contexts: List[str]) -> Any:
        """Extract a numeric value for a given tag and contexts."""
        namespaces = {
            "xbrl": "http://www.xbrl.org/2003/instance",
            "jpcrp": "http://disclosure.edinet-fsa.go.jp/jpcrp/2018-08-31",
            "jpcrp_cor": "http://disclosure.edinet-fsa.go.jp/jpcrp/2020-11-30",
        }

        # Try to find the element
        for ns, ns_uri in namespaces.items():
            full_tag = f"{{{ns_uri}}}{tag_name}" if ns != "xbrl" else tag_name
            elements = root.findall(f".//{full_tag}")
            for elem in elements:
                ctx_ref = elem.get("contextRef")
                if ctx_ref in contexts:
                    text = elem.text
                    if text:
                        try:
                            return float(text)
                        except ValueError:
                            pass

        # Fallback without namespace
        elements = root.findall(f".//{tag_name}")
        for elem in elements:
            ctx_ref = elem.get("contextRef")
            if ctx_ref in contexts:
                text = elem.text
                if text:
                    try:
                        return float(text)
                    except ValueError:
                        pass

        return None


__all__ = ["EdinetStockDividendParser"]
