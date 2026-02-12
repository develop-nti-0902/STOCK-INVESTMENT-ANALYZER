"""XML/XBRL 解析ユーティリティ.

`XMLParserMixin` は `lxml` を利用した共通パーシング/抽出メソッドを提供します.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from lxml import etree


class XMLParserMixin:
    """XML/XBRL解析で共通に使うユーティリティを提供するMixin.

    `lxml` を使ってパースとテキスト抽出を行います.
    """

    @staticmethod
    def parse_xml(file_path: str) -> etree._Element:
        """ファイルをパースしてルート要素を返す.

        Args:
            file_path: XML/XBRL ファイルパス

        Returns:
            lxml のルート要素
        """
        parser = etree.XMLParser(recover=True, ns_clean=True)
        with open(file_path, "rb") as fh:
            tree = etree.parse(fh, parser=parser)
        return tree.getroot()

    @staticmethod
    def extract_text(
        element: etree._Element,
        xpath: str,
        namespaces: Optional[Dict[str, str]] = None,
    ) -> List[str]:
        """XPath で要素を抽出してテキストを返す.

        Args:
            element: 検索対象のルート要素
            xpath: XPath 式
            namespaces: 名前空間辞書

        Returns:
            マッチした要素のテキスト一覧（空文字は除外）
        """
        nodes = element.xpath(xpath, namespaces=namespaces)
        texts: List[str] = []
        for n in nodes:
            if isinstance(n, etree._ElementUnicodeResult) or isinstance(n, str):
                text = str(n).strip()
            elif isinstance(n, etree._Element):
                text = (n.text or "").strip()
            else:
                text = str(n).strip()
            if text:
                texts.append(text)
        return texts

    def determine_consolidation(self, root: etree._Element, contexts: List[str]) -> Optional[bool]:
        """与えられたコンテキストから連結/非連結を判定して True/False/None を返す共通実装.

        balance_sheet と profit_and_loss で使われる判定ロジックを統一する。
        """
        for ctx in contexts:
            if "Consolidated" in ctx or "ConsolidatedMember" in ctx:
                return True
            if "NonConsolidated" in ctx or "NonConsolidatedMember" in ctx:
                return False
        return None

    def get_period_end_date(self, root: etree._Element, contexts: List[str]) -> Optional[date]:
        """コンテキストから期間終了日を抽出する共通実装.

        - まず `xbrli:endDate` (duration ベース) を試みる。
        - 見つからなければ `instant`（balance_sheet の形式）を試行する。
        - 最後にドキュメント内の最初の `instant` をフォールバックとして使う。
        """
        # duration ベースの endDate を優先して探す
        for context_ref in contexts:
            try:
                xpath_query = f"//xbrli:context[@id='{context_ref}']//xbrli:endDate"
                elements = root.xpath(
                    xpath_query, namespaces={"xbrli": "http://www.xbrl.org/2003/instance"}
                )
                if elements:
                    date_text = elements[0].text
                    if date_text:
                        return datetime.strptime(date_text, "%Y-%m-%d").date()
            except Exception:
                continue

        # instant ベースでコンテキストから探す（balance_sheet と同様）
        for ctx_id in contexts:
            try:
                context_xpath = f".//*[local-name() = 'context'][@id = '{ctx_id}']"
                context_nodes = root.xpath(context_xpath)
                if not context_nodes:
                    continue

                instant_nodes = context_nodes[0].xpath(".//*[local-name() = 'instant']")
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
            except Exception:
                continue

        # ドキュメント全体の最初の instant をフォールバックとして使用
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

    def extract_numeric_from_xbrl(
        self, parsed_xbrl: Any, tag_candidates: List[str], contexts: List[str]
    ) -> Optional[float]:
        """単純な数値抽出ユーティリティ.

        `parsed_xbrl.get_data_by_context_ref(tag, ctx)` を試し、取得値を float に変換して返す。
        フォールバックの複雑な探索は行わない。
        """
        for tag in tag_candidates:
            for ctx in contexts:
                try:
                    data = parsed_xbrl.get_data_by_context_ref(tag, ctx)
                    if not data:
                        continue
                    candidate = data
                    if isinstance(data, (list, tuple)) and data:
                        candidate = data[0]

                    val = None
                    if hasattr(candidate, "get_value"):
                        val = candidate.get_value()
                    elif hasattr(candidate, "value"):
                        val = candidate.value
                    elif hasattr(candidate, "text"):
                        val = candidate.text

                    if val is not None:
                        try:
                            return float(str(val).replace(",", ""))
                        except Exception:
                            continue
                except Exception:
                    continue
        return None
