"""EDINET の XBRL から貸借対照表を抽出するパーサーモジュール.

当モジュールは XBRL を解析し、指定した年度キー（current）に
対応する貸借対照表の主要値を抽出して辞書で返します。
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


class EdinetBalanceSheetParser(BaseParser, XMLParserMixin):
    """XBRL から貸借対照表を抽出するパーサー.

    現行年度（current）の1年分を返します。
    実運用では XBRL の名前空間・要素名に合わせて XPath を調整してください。
    """

    # 年度キーを balance_sheet に合わせる
    YEARS = ["current"]

    # コンテキスト候補パターン（balance_sheet は Instant ベース）
    CONTEXT_PATTERNS = {
        "current": [
            "CurrentYearInstant",
            "CurrentYearInstant_ConsolidatedMember",
            "CurrentYearInstant_NonConsolidatedMember",
        ],
    }

    # XBRLタグの候補マッピング
    XBRL_TAGS = {
        "total_assets": [
            "jppfs_cor:TotalAssets",
            "jpcrp_cor:TotalAssetsSummaryOfBusinessResults",
        ],
        "net_assets": [
            "jppfs_cor:NetAssets",
            "jpcrp_cor:NetAssetsSummaryOfBusinessResults",
        ],
        "shareholders_equity": [
            "jppfs_cor:ShareholdersEquity",
            "jpcrp_cor:ShareholdersEquitySummaryOfBusinessResults",
        ],
        "bps": [
            "jppfs_cor:NetAssetsPerShareSummary",
            "jpcrp_cor:NetAssetsPerShareSummaryOfBusinessResults",
        ],
        "equity_ratio": [
            "jppfs_cor:EquityToAssetRatio",
            "jpcrp_cor:EquityToAssetRatioSummaryOfBusinessResults",
        ],
    }

    def parse_root(self, root: etree._Element, parsed_xbrl: Any) -> Dict[str, Any]:
        """パース済の lxml ルート要素と事前に作成された `parsed_xbrl` を受け取り年度別の貸借対照表辞書を返す.

        注意: `parsed_xbrl` は外部で一度だけ構築して渡すことを想定します。
        """
        # ファイルから実際に使用可能なコンテキストを抽出
        all_contexts = self._get_all_available_contexts(root)

        result: Dict[str, Any] = {}
        # 現行年度分のデータを取得
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
                    # Collect all contexts that contain the pattern
                    matched_contexts.append(context)
        return matched_contexts

    def parse_single_year(
        self,
        parsed_xbrl: Any,
        root: etree._Element,
        contexts: List[str],
        year_key: str,
    ) -> Dict[str, Any]:
        """指定年度（contexts）から貸借対照表関連の各項目を抽出して辞書で返す."""
        total_assets = self.extract_total_assets(parsed_xbrl, root, contexts)
        net_assets = self.extract_net_assets(parsed_xbrl, root, contexts)
        shareholders_equity = self.extract_shareholders_equity(parsed_xbrl, root, contexts)
        bps = self.extract_bps(parsed_xbrl, root, contexts)
        equity_ratio = self.extract_equity_ratio(parsed_xbrl, root, contexts)
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
            "total_assets": total_assets,
            "net_assets": net_assets,
            "shareholders_equity": shareholders_equity,
            "bps": bps,
            "equity_ratio": equity_ratio,
            "period_end": period_end,
            "period_end_date": period_end_date,
            "consolidation": consolidation,
        }

    def extract_total_assets(
        self, parsed_xbrl: Any, root: etree._Element, contexts: List[str]
    ) -> Optional[float]:
        """総資産（Total Assets）を抽出して返す。見つからなければ None を返す."""
        return self.extract_numeric_from_xbrl(
            parsed_xbrl, self.XBRL_TAGS.get("total_assets", []), contexts
        )

    def extract_net_assets(
        self, parsed_xbrl: Any, root: etree._Element, contexts: List[str]
    ) -> Optional[float]:
        """純資産（Net Assets）を抽出して返す。見つからなければ None を返す."""
        return self.extract_numeric_from_xbrl(
            parsed_xbrl, self.XBRL_TAGS.get("net_assets", []), contexts
        )

    def extract_shareholders_equity(
        self, parsed_xbrl: Any, root: etree._Element, contexts: List[str]
    ) -> Optional[float]:
        """株主資本（Shareholders Equity）を抽出して返す。見つからなければ None を返す."""
        return self.extract_numeric_from_xbrl(
            parsed_xbrl, self.XBRL_TAGS.get("shareholders_equity", []), contexts
        )

    def extract_bps(
        self, parsed_xbrl: Any, root: etree._Element, contexts: List[str]
    ) -> Optional[float]:
        """BPS（1株当たり純資産）を抽出して返す。見つからなければ None を返す."""
        return self.extract_numeric_from_xbrl(parsed_xbrl, self.XBRL_TAGS.get("bps", []), contexts)

    def extract_equity_ratio(
        self, parsed_xbrl: Any, root: etree._Element, contexts: List[str]
    ) -> Optional[float]:
        """自己資本比率（Equity to Asset Ratio）を抽出して返す。見つからなければ None を返す."""
        return self.extract_numeric_from_xbrl(
            parsed_xbrl, self.XBRL_TAGS.get("equity_ratio", []), contexts
        )


__all__ = ["EdinetBalanceSheetParser"]
