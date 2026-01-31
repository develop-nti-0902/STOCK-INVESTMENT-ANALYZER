from __future__ import annotations

from pathlib import Path

from lxml import etree

from app.services.core.parsers.xml_parser_mixin import XMLParserMixin


def test_parse_xml_and_extract_text(tmp_path: Path):
    xml = "<root><child>hello</child></root>"
    p = tmp_path / "sample.xml"
    p.write_bytes(xml.encode("utf-8"))

    root = XMLParserMixin.parse_xml(str(p))
    assert isinstance(root, etree._Element)
    assert root.tag == "root"

    texts = XMLParserMixin.extract_text(root, "./child/text()")
    assert texts == ["hello"]


def test_parse_xml_recover_on_malformed(tmp_path: Path):
    # malformed XML should still be parsed with recover=True
    bad = "<root><child>oops"
    p = tmp_path / "bad.xml"
    p.write_bytes(bad.encode("utf-8"))

    root = XMLParserMixin.parse_xml(str(p))
    assert isinstance(root, etree._Element)


def test_extract_text_with_namespace():
    xml = '<root xmlns:ns="http://example.com"><ns:item>val</ns:item></root>'
    root = etree.fromstring(xml.encode("utf-8"))
    texts = XMLParserMixin.extract_text(
        root, ".//ns:item/text()", namespaces={"ns": "http://example.com"}
    )
    assert texts == ["val"]
