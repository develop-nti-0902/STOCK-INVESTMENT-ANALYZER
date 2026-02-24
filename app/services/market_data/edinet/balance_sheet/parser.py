"""EDINET の XBRL から貸借対照表を抽出するパーサーモジュール.

当モジュールは XBRL を解析し、指定した年度キー（current, prior1..prior4）に
対応する貸借対照表の主要値を抽出して辞書で返します。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from lxml import etree

from app.services.data_synchronization._core.parsers.base_parser import BaseParser
from app.services.data_synchronization._core.parsers.xml_parser_mixin import XMLParserMixin

# Module-level placeholder for external XBRL parser class; tests may monkeypatch this.
XbrlParser = None


class EdinetBalanceSheetParser(BaseParser, XMLParserMixin):
    """XBRL から貸借対照表を抽出するパーサー.

    現行年度（current）と過去4年（prior1..prior4）の計5年分を返します。
    実運用では XBRL の名前空間・要素名に合わせて XPath を調整してください。
    """

    # 年度キーを profit_and_loss と揃える（将来の拡張性のため）
    YEARS = ["current"]
    # YEARS = ["current", "prior1", "prior2", "prior3", "prior4"]

    # 年度ごとのコンテキストパターン（優先順）
    CONTEXT_PATTERNS = {
        "current": [
            "CurrentYearInstant",
            "CurrentYearInstant_ConsolidatedMember",
            "CurrentYearInstant_NonConsolidatedMember",
        ],
    }
    # CONTEXT_PATTERNS = {
    #     "current": [
    #         "CurrentYearInstant",
    #         "CurrentYearInstant_ConsolidatedMember",
    #         "CurrentYearInstant_NonConsolidatedMember",
    #     ],
    #     "prior1": [
    #         "Prior1YearInstant",
    #         "Prior1YearInstant_ConsolidatedMember",
    #         "Prior1YearInstant_NonConsolidatedMember",
    #     ],
    #     "prior2": [
    #         "Prior2YearInstant",
    #         "Prior2YearInstant_ConsolidatedMember",
    #         "Prior2YearInstant_NonConsolidatedMember",
    #     ],
    #     "prior3": [
    #         "Prior3YearInstant",
    #         "Prior3YearInstant_ConsolidatedMember",
    #         "Prior3YearInstant_NonConsolidatedMember",
    #     ],
    #     "prior4": [
    #         "Prior4YearInstant",
    #         "Prior4YearInstant_ConsolidatedMember",
    #         "Prior4YearInstant_NonConsolidatedMember",
    #     ],
    # }

    # XBRLタグの候補マッピング
    XBRL_TAGS = {
        "assets": [
            "jpcrp_cor:TotalAssetsSummaryOfBusinessResults",
            "jppfs_cor:Assets",
        ],
        "liabilities": [
            "jppfs_cor:Liabilities",
        ],
        "equity": [
            "jppfs_cor:NetAssets",
            "jppfs_cor:ShareholdersEquity",
        ],
    }

    def parse_root(self, root: etree._Element, parsed_xbrl: Any) -> Dict[str, Any]:
        """パース済の lxml ルート要素と事前に作成された `parsed_xbrl` を受け取り年度別貸借対照表辞書を返す.

        注意: `parsed_xbrl` は外部で一度だけ構築して渡すことを想定します。
        """
        # ファイルから実際に使用可能なコンテキストを抽出
        all_contexts = self._get_all_available_contexts(root)

        result: Dict[str, Any] = {}
        for year_key in self.YEARS:
            year_contexts = self._get_contexts_for_year(year_key, all_contexts)
            if year_contexts:
                result[year_key] = self.parse_single_year(
                    parsed_xbrl, root, year_contexts, year_key
                )
            else:
                result[year_key] = None
        return result

    def _get_all_available_contexts(self, root: etree._Element) -> List[str]:
        """XBRL ルート要素から利用可能な contextRef をすべて抽出して返す."""
        context_refs = set()
        for elem in root.xpath(".//*[@contextRef]"):
            ref = elem.get("contextRef")
            if ref:
                context_refs.add(ref)
        return list(context_refs)

    def _get_contexts_for_year(self, year_key: str, all_contexts: List[str]) -> List[str]:
        patterns = self.CONTEXT_PATTERNS.get(year_key, [])
        prioritized = []

        # パターンに一致するコンテキストを優先順に追加
        for pattern in patterns:
            for ctx in sorted(all_contexts):
                if pattern in ctx and ctx not in prioritized:
                    prioritized.append(ctx)

        return prioritized

    def parse_single_year(
        self,
        parsed_xbrl: Any,
        root: etree._Element,
        contexts: List[str],
        year_key: str,
    ) -> Dict[str, Any]:
        """指定年度（contexts）から貸借対照表の各項目を抽出して辞書で返す."""
        assets = self.extract_assets(parsed_xbrl, contexts)
        liabilities = self.extract_liabilities(parsed_xbrl, contexts)
        equity = self.extract_equity(parsed_xbrl, contexts)
        period_end = self.get_period_end_date(root, contexts)
        consolidation = self.determine_consolidation(root, contexts)
        metrics = self.calculate_metrics(assets, liabilities, equity)

        # 正規化: period_end_date を追加して date 型に揃えて返す
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
            "assets": assets,
            "liabilities": liabilities,
            "equity": equity,
            "period_end": period_end,
            "period_end_date": period_end_date,
            "consolidation": consolidation,
            "metrics": metrics,
        }

    def validate_data(self, data: Any) -> bool:
        """与えられたデータがパーサーで扱える形式かどうかを検証する."""
        try:
            root = data if isinstance(data, etree._Element) else self.parse_xml(data)
        except Exception:
            return False
        # 簡易検証: contextRef を持つ要素が存在し、かつ context 要素が存在すること
        context_refs = root.xpath(".//*[@contextRef]")
        contexts = root.xpath(".//*[local-name() = 'context']")
        return len(context_refs) > 0 and len(contexts) > 0

    def extract_assets(self, parsed_xbrl: Any, contexts: List[str]) -> Optional[float]:
        """資産額を抽出して浮動小数点で返す."""
        return self.extract_numeric_from_xbrl(parsed_xbrl, self.XBRL_TAGS["assets"], contexts)

    def extract_liabilities(self, parsed_xbrl: Any, contexts: List[str]) -> Optional[float]:
        """負債額を抽出して浮動小数点で返す."""
        return self.extract_numeric_from_xbrl(parsed_xbrl, self.XBRL_TAGS["liabilities"], contexts)

    def extract_equity(self, parsed_xbrl: Any, contexts: List[str]) -> Optional[float]:
        """純資産（株主資本）を抽出して浮動小数点で返す."""
        return self.extract_numeric_from_xbrl(parsed_xbrl, self.XBRL_TAGS["equity"], contexts)

    def calculate_metrics(
        self,
        assets: Optional[float],
        liabilities: Optional[float],
        equity: Optional[float],
    ) -> Dict[str, Optional[float]]:
        """補助指標（運転資本、自己資本比率等）を計算して返す."""
        assets_val = assets or 0.0
        liabilities_val = liabilities or 0.0
        equity_val = equity or 0.0
        return {
            "working_capital": (
                None if assets is None or liabilities is None else assets_val - liabilities_val
            ),
            "equity_ratio": (None if assets_val == 0 else (equity_val / assets_val)),
            "net_assets": equity_val,
        }
