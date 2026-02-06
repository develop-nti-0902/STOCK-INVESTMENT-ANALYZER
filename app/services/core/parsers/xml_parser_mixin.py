"""XML/XBRL 解析ユーティリティ.

`XMLParserMixin` は `lxml` を利用した共通パーシング/抽出メソッドを提供します.
"""

from __future__ import annotations

from typing import Dict, List, Optional

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
