from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from edinet_xbrl.edinet_xbrl_parser import EdinetXbrlParser as XbrlParser
from lxml import etree

from app.services.core.parsers.base_parser import BaseParser
from app.services.core.parsers.xml_parser_mixin import XMLParserMixin


class EdinetBalanceSheetParser(BaseParser, XMLParserMixin):
    """XBRL から貸借対照表を抽出するパーサー。

    現行年度（current）と過去4年（prior1..prior4）の計5年分を返します。
    実運用では XBRL の名前空間・要素名に合わせて XPath を調整してください。
    """

    YEARS = ["current", "prior1", "prior2", "prior3", "prior4"]

    # 年度ごとのコンテキストパターン（優先順）
    CONTEXT_PATTERNS = {
        "current": [
            "CurrentYearInstant",
            "CurrentYearInstant_ConsolidatedMember",
            "CurrentYearInstant_NonConsolidatedMember",
        ],
        "prior1": [
            "Prior1YearInstant",
            "Prior1YearInstant_ConsolidatedMember",
            "Prior1YearInstant_NonConsolidatedMember",
        ],
        "prior2": [
            "Prior2YearInstant",
            "Prior2YearInstant_ConsolidatedMember",
            "Prior2YearInstant_NonConsolidatedMember",
        ],
        "prior3": [
            "Prior3YearInstant",
            "Prior3YearInstant_ConsolidatedMember",
            "Prior3YearInstant_NonConsolidatedMember",
        ],
        "prior4": [
            "Prior4YearInstant",
            "Prior4YearInstant_ConsolidatedMember",
            "Prior4YearInstant_NonConsolidatedMember",
        ],
    }

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

    def parse(self, data: Any) -> Dict[str, Any]:
        # XBRLファイルをパース
        xbrl_parser = XbrlParser()
        if isinstance(data, str):
            parsed_xbrl = xbrl_parser.parse_file(data)
            root = self.parse_xml(data)
        elif isinstance(data, Path):
            # Pathオブジェクトの場合は文字列に変換
            file_path = str(data)
            parsed_xbrl = xbrl_parser.parse_file(file_path)
            root = self.parse_xml(file_path)
        elif isinstance(data, etree._Element):
            # etree._Element の場合は一時ファイルに書き出してパース
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".xbrl", delete=False
            ) as f:
                f.write(etree.tostring(data, encoding="utf-8"))
                tmp_path = f.name
            parsed_xbrl = xbrl_parser.parse_file(tmp_path)
            root = data
        else:
            raise TypeError(
                "data must be file path (str or Path) or lxml root element"
            )

        # ファイルから実際に使用可能なコンテキストを抽出
        all_contexts = self._get_all_available_contexts(root)

        result: Dict[str, Any] = {}
        # 全5年分のデータを取得
        for year_key in self.YEARS:
            year_contexts = self._get_contexts_for_year(year_key, all_contexts)
            if year_contexts:  # コンテキストが存在する年度のみ処理
                result[year_key] = self.parse_single_year(
                    parsed_xbrl, root, year_contexts, year_key
                )
            else:
                result[year_key] = None
        return result

    def _get_all_available_contexts(self, root: etree._Element) -> List[str]:
        """XBRLファイルから利用可能な全コンテキストIDを抽出する。"""
        context_refs = set()
        for elem in root.xpath(".//*[@contextRef]"):
            ref = elem.get("contextRef")
            if ref:
                context_refs.add(ref)
        return list(context_refs)

    def _get_contexts_for_year(
        self, year_key: str, all_contexts: List[str]
    ) -> List[str]:
        """特定の年度に対応するコンテキストを優先順に取得する。"""
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
        assets = self.extract_assets(parsed_xbrl, contexts)
        liabilities = self.extract_liabilities(parsed_xbrl, contexts)
        equity = self.extract_equity(parsed_xbrl, contexts)
        period_end = self.get_period_end_date(root, contexts)
        consolidation = self.determine_consolidation(root, contexts)
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
        # 簡易検証: contextRef を持つ要素が存在し、かつ context 要素が存在すること
        context_refs = root.xpath(".//*[@contextRef]")
        contexts = root.xpath(".//*[local-name() = 'context']")
        return len(context_refs) > 0 and len(contexts) > 0

    def extract_assets(
        self, parsed_xbrl: Any, contexts: List[str]
    ) -> Optional[float]:
        return self._extract_numeric_from_xbrl(
            parsed_xbrl, self.XBRL_TAGS["assets"], contexts
        )

    def extract_liabilities(
        self, parsed_xbrl: Any, contexts: List[str]
    ) -> Optional[float]:
        return self._extract_numeric_from_xbrl(
            parsed_xbrl, self.XBRL_TAGS["liabilities"], contexts
        )

    def extract_equity(
        self, parsed_xbrl: Any, contexts: List[str]
    ) -> Optional[float]:
        return self._extract_numeric_from_xbrl(
            parsed_xbrl, self.XBRL_TAGS["equity"], contexts
        )

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
        self, root: etree._Element, contexts: List[str]
    ) -> Optional[bool]:
        # コンテキストに Consolidated が含まれていれば True
        for ctx in contexts:
            if "Consolidated" in ctx:
                return True
            if "NonConsolidated" in ctx:
                return False
        return None

    def get_period_end_date(
        self, root: etree._Element, contexts: List[str]
    ) -> Optional[date]:
        """コンテキストから期末日を取得する。

        戻り値は ISO 文字列ではなく datetime.date を返します。
        """
        # 優先するコンテキストから instant 日付を抽出
        for ctx_id in contexts:
            # context 要素を探す
            context_xpath = f".//*[local-name() = 'context'][@id = '{ctx_id}']"
            context_nodes = root.xpath(context_xpath)
            if not context_nodes:
                continue

            # context 内の instant 要素を探す
            instant_xpath = ".//*[local-name() = 'instant']"
            instant_nodes = context_nodes[0].xpath(instant_xpath)
            if instant_nodes and instant_nodes[0].text:
                date_str = instant_nodes[0].text.strip()
                try:
                    dt = datetime.fromisoformat(date_str)
                    return dt.date()
                except Exception:
                    try:
                        dt = datetime.strptime(date_str, "%Y-%m-%d")
                        return dt.date()
                    except Exception:
                        pass

        # フォールバック: 最初の instant を使用
        instant_nodes = root.xpath(".//*[local-name() = 'instant']")
        if instant_nodes and instant_nodes[0].text:
            date_str = instant_nodes[0].text.strip()
            try:
                dt = datetime.fromisoformat(date_str)
                return dt.date()
            except Exception:
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%d")
                    return dt.date()
                except Exception:
                    pass

        return None

    def _extract_numeric_from_xbrl(
        self,
        parsed_xbrl: Any,
        tag_candidates: List[str],
        contexts: List[str],
    ) -> Optional[float]:
        """XBRLパーサーを使用してコンテキスト付きでデータを取得する。"""
        for tag in tag_candidates:
            for ctx in contexts:
                try:
                    data = parsed_xbrl.get_data_by_context_ref(tag, ctx)
                    if data:
                        value = data.get_value()
                        if value is not None:
                            try:
                                return float(value)
                            except Exception:
                                pass
                except Exception:
                    continue
        return None
