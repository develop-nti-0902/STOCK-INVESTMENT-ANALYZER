"""EDINET XBRL からキャッシュフロー（営業活動）を抽出するパーサーモジュール."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from lxml import etree

from app.services.core.parsers.base_parser import BaseParser
from app.services.core.parsers.xml_parser_mixin import XMLParserMixin

# Module-level placeholder for external XBRL parser class; tests may monkeypatch this.
XbrlParser = None


class EdinetCashFlowStatementParser(BaseParser, XMLParserMixin):
    """XBRL からキャッシュフローを抽出する簡易パーサー."""

    YEARS = ["current", "prior1", "prior2", "prior3", "prior4"]

    CONTEXT_PATTERNS = {
        "current": [
            "CurrentYearDuration",
            "CurrentYearDuration_ConsolidatedMember",
            "CurrentYearDuration_NonConsolidatedMember",
        ],
        "prior1": [
            "Prior1YearDuration",
            "Prior1YearDuration_ConsolidatedMember",
            "Prior1YearDuration_NonConsolidatedMember",
        ],
        "prior2": [
            "Prior2YearDuration",
            "Prior2YearDuration_ConsolidatedMember",
            "Prior2YearDuration_NonConsolidatedMember",
        ],
        "prior3": [
            "Prior3YearDuration",
            "Prior3YearDuration_ConsolidatedMember",
            "Prior3YearDuration_NonConsolidatedMember",
        ],
        "prior4": [
            "Prior4YearDuration",
            "Prior4YearDuration_ConsolidatedMember",
            "Prior4YearDuration_NonConsolidatedMember",
        ],
    }

    XBRL_TAGS = {
        "operating_cf": [
            "jppfs_cor:NetCashProvidedByUsedInOperatingActivities",
        ]
    }

    def parse_root(self, root: etree._Element, parsed_xbrl: Any) -> Dict[str, Any]:
        all_contexts = self._get_all_available_contexts(root)

        result: Dict[str, Any] = {}
        for year_key in self.YEARS:
            contexts = self._get_contexts_for_year(year_key, all_contexts)
            if contexts:
                result[year_key] = self.parse_single_year(parsed_xbrl, root, contexts, year_key)
            else:
                result[year_key] = None
        return result

    def _get_all_available_contexts(self, root: etree._Element) -> List[str]:
        context_refs = set()
        for elem in root.xpath(".//*[@contextRef]"):
            ref = elem.get("contextRef")
            if ref:
                context_refs.add(ref)
        return list(context_refs)

    def _get_contexts_for_year(self, year_key: str, all_contexts: List[str]) -> List[str]:
        patterns = self.CONTEXT_PATTERNS.get(year_key, [])
        prioritized: List[str] = []
        for pattern in patterns:
            for ctx in sorted(all_contexts):
                if pattern in ctx and ctx not in prioritized:
                    prioritized.append(ctx)
        return prioritized

    def parse_single_year(
        self, parsed_xbrl: Any, root: etree._Element, contexts: List[str], year_key: str
    ) -> Dict[str, Any]:
        operating_cf = self.extract_numeric_from_xbrl(
            parsed_xbrl, self.XBRL_TAGS["operating_cf"], contexts
        )
        period_end = self.get_period_end_date(root, contexts)
        consolidation = self.determine_consolidation(root, contexts)

        period_end_date: Optional[date] = None
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
            "operating_cf": operating_cf,
            "period_end": period_end,
            "period_end_date": period_end_date,
            "consolidation": consolidation,
        }

    def validate_data(self, data: Any) -> bool:
        try:
            root = data if isinstance(data, etree._Element) else self.parse_xml(data)
        except Exception:
            return False
        context_refs = root.xpath(".//*[@contextRef]")
        contexts = root.xpath(".//*[local-name() = 'context']")
        return len(context_refs) > 0 and len(contexts) > 0


__all__ = ["EdinetCashFlowStatementParser"]
