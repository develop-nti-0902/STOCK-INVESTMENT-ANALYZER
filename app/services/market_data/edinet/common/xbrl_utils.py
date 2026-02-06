"""XBRL/XML のユーティリティ関数群.

ファイル探索やコンテキスト抽出の簡易実装を提供します。
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from lxml import etree


def find_xbrl_files(directory: Path, extensions: Optional[List[str]] = None) -> List[Path]:
    """指定ディレクトリ内の XBRL ファイルを再帰検索して返す.

    Args:
        directory: 検索開始ディレクトリ
        extensions: 探索する拡張子（小文字、先頭にピリオド不要）

    Returns:
        見つかったファイルパスのリスト
    """
    if extensions is None:
        extensions = ["xbrl", "xml"]

    result: List[Path] = []
    for p in directory.rglob("*"):
        if p.is_file():
            if p.suffix.lstrip(".").lower() in extensions:
                result.append(p)
    return sorted(result)


def extract_contexts(xbrl_content: str) -> Dict[str, Dict[str, str]]:
    """XBRL のコンテキスト要素を抽出する.

    簡易実装で、各 `context` 要素の `id` 属性をキーに、period と entity の文字列を返す。

    Args:
        xbrl_content: XBRL/XML の文字列

    Returns:
        { context_id: {"period": "...", "entity": "...", "xml": "..."} }
    """
    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(xbrl_content.encode("utf-8"), parser=parser)

    contexts: Dict[str, Dict[str, str]] = {}

    # XPath で名前空間を気にせず local-name() を使う
    context_elems = root.xpath("//*[local-name() = 'context']")
    for ce in context_elems:
        cid = ce.get("id") or ""
        # period を文字列化（xpath を使って限定的に検索）
        period_elems = ce.xpath('.//*[local-name() = "period"]')
        period_elem = period_elems[0] if period_elems else None
        period_txt = (
            etree.tostring(period_elem, encoding="unicode") if period_elem is not None else ""
        )

        entity_elems = ce.xpath('.//*[local-name() = "entity"]')
        entity_elem = entity_elems[0] if entity_elems else None
        entity_txt = (
            etree.tostring(entity_elem, encoding="unicode") if entity_elem is not None else ""
        )

        contexts[cid] = {
            "period": period_txt,
            "entity": entity_txt,
            "xml": etree.tostring(ce, encoding="unicode"),
        }

    return contexts
