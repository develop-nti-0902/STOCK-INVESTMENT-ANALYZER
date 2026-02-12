"""EDINET の XBRL から損益・キャッシュフローを抽出するパーサーモジュール.

当モジュールは XBRL を解析し、指定した年度キー（current, prior1..prior4）に
対応する損益計算書とキャッシュフロー計算書の主要値を抽出して辞書で返します。
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from lxml import etree

from app.services.core.parsers.base_parser import BaseParser
from app.services.core.parsers.xml_parser_mixin import XMLParserMixin

# Module-level placeholder for external XBRL parser class; tests may monkeypatch this.
XbrlParser = None


class EdinetProfitAndLossParser(BaseParser, XMLParserMixin):
    """XBRL から損益・キャッシュフローを抽出するパーサー.

    現行年度（current）と過去4年（prior1..prior4）の計5年分を返します。
    実運用では XBRL の名前空間・要素名に合わせて XPath を調整してください。
    """

    YEARS = ["current", "prior1", "prior2", "prior3", "prior4"]

    # 年度ごとのコンテキストパターン（優先順）- Duration ベース
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

    # XBRLタグの候補マッピング
    XBRL_TAGS = {
        "eps": [
            "jpcrp_cor:BasicEarningsLossPerShareSummaryOfBusinessResults",
        ],
        "operating_profit": [
            "jppfs_cor:NetCashProvidedByUsedInOperatingActivities",
        ],
    }

    def parse_root(self, root: etree._Element, parsed_xbrl: Any) -> Dict[str, Any]:
        """パース済の lxml ルート要素と事前に作成された `parsed_xbrl` を受け取り年度別の損益辞書を返す.

        注意: `parsed_xbrl` は外部で一度だけ構築して渡すことを想定します。
        """

        # ファイルから実際に使用可能なコンテキストを抽出
        all_contexts = self._get_all_available_contexts(root)

        result: Dict[str, Any] = {}
        # 全5年分のデータを取得。balance_sheet と同様に、年キーに対応する
        # コンテキストが見つからなければ None を格納する形式に合わせる。
        for year_key in self.YEARS:
            year_contexts = self._get_contexts_for_year(year_key, all_contexts)
            if year_contexts:
                result[year_key] = self.parse_single_year(
                    parsed_xbrl, root, year_contexts, year_key
                )
            else:
                result[year_key] = None
        return result

    def validate_data(self, data: Any) -> bool:
        """データの妥当性を検証する（BaseParserの抽象メソッドの実装）."""
        if data is None:
            return False
        if isinstance(data, (str, Path)):
            # ファイルパスの場合、ファイルが存在するかチェック
            if isinstance(data, str):
                path = Path(data)
            else:
                path = data
            return path.exists() and path.is_file()
        elif isinstance(data, etree._Element):
            # lxml要素の場合は有効とみなす
            return True
        return False

    def _get_all_available_contexts(self, root: etree._Element) -> List[str]:
        """XBRL ルート要素から利用可能な contextRef をすべて抽出して返す."""
        context_refs = set()
        for elem in root.xpath(".//*[@contextRef]"):
            ref = elem.get("contextRef")
            if ref:
                context_refs.add(ref)
        return list(context_refs)

    def _get_contexts_for_year(self, year_key: str, all_contexts: List[str]) -> List[str]:
        """特定年度で利用・マッチするコンテキスト群を返す."""
        patterns = self.CONTEXT_PATTERNS.get(year_key, [])
        matched_contexts = []

        for pattern in patterns:
            for context in all_contexts:
                if pattern in context:
                    # Collect all contexts that contain the pattern (do not stop at first match)
                    matched_contexts.append(context)
                    # continue scanning other contexts to gather all relevant matches
        return matched_contexts

    def parse_single_year(
        self,
        parsed_xbrl: Any,
        root: etree._Element,
        contexts: List[str],
        year_key: str,
    ) -> Dict[str, Any]:
        """指定年度（contexts）から損益関連の各項目を抽出して辞書で返す."""
        eps = self.extract_eps(parsed_xbrl, root, contexts)
        operating_profit = self.extract_operating_profit(parsed_xbrl, root, contexts)
        consolidation = self.determine_consolidation(root, contexts)
        period_end = self.get_period_end_date(root, contexts)

        # 正規化: period_end_date を常に含める（可能な限り date 型にする）
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
            "eps": eps,
            "operating_profit": operating_profit,
            "period_end": period_end,
            "period_end_date": period_end_date,
            "consolidation": consolidation,
        }

    def extract_eps(
        self, parsed_xbrl: Any, root: etree._Element, contexts: List[str]
    ) -> Optional[float]:
        """EPS（1株当たり当期純利益）を抽出して返す。見つからなければ None を返す."""
        return self.extract_numeric_from_xbrl(parsed_xbrl, self.XBRL_TAGS.get("eps", []), contexts)

    def extract_operating_profit(
        self, parsed_xbrl: Any, root: etree._Element, contexts: List[str]
    ) -> Optional[float]:
        """営業活動によるキャッシュフロー等の指標を抽出して返す。見つからなければ None を返す."""
        return self.extract_numeric_from_xbrl(
            parsed_xbrl, self.XBRL_TAGS.get("operating_profit", []), contexts
        )


__all__ = ["EdinetProfitAndLossParser"]
