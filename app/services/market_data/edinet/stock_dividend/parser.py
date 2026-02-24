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
        context_refs = set()
        for elem in root.xpath(".//*[@contextRef]"):
            ref = elem.get("contextRef")
            if ref:
                context_refs.add(ref)
        return list(context_refs)

    def _get_contexts_for_year(self, year_key: str, all_contexts: List[str]) -> List[str]:
        patterns = self.CONTEXT_PATTERNS.get(year_key, [])
        matched = []
        for p in patterns:
            for c in all_contexts:
                if p in c:
                    matched.append(c)
        return matched

    def parse_single_year(
        self, parsed_xbrl: Any, root: etree._Element, contexts: List[str], year_key: str
    ) -> Dict[str, Any]:
        """Parse a single year's dividend data from provided XBRL contexts."""
        dividend = self.extract_dividend(parsed_xbrl, root, contexts)
        consolidation = self.determine_consolidation(root, contexts)
        period_end = self.get_period_end_date(root, contexts)

        period_end_date = None
        try:
            if isinstance(period_end, datetime):
                period_end_date = period_end.date()
            elif isinstance(period_end, date):
                period_end_date = period_end
            elif isinstance(period_end, str):
                try:
                    period_end_date = datetime.fromisoformat(period_end).date()
                except Exception:
                    try:
                        period_end_date = datetime.strptime(period_end, "%Y-%m-%d").date()
                    except Exception:
                        period_end_date = None
        except Exception:
            period_end_date = None

        return {
            "dividend_actual": dividend,
            "period_end": period_end,
            "period_end_date": period_end_date,
            "consolidation": consolidation,
        }

    def extract_dividend(
        self, parsed_xbrl: Any, root: etree._Element, contexts: List[str]
    ) -> Optional[float]:
        """Extract dividend numeric value from XBRL for provided contexts."""
        return self.extract_numeric_from_xbrl(
            parsed_xbrl, self.XBRL_TAGS.get("dividend_actual", []), contexts
        )


__all__ = ["EdinetStockDividendParser"]
