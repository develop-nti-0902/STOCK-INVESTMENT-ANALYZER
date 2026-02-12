"""共通パーサーの抽象基底クラスモジュール.

各パーサーはここから継承し、`parse` と `validate_data` を実装します.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseParser(ABC):
    """共通パーサーの抽象基底クラス.

    サブクラスは `parse` と `validate_data` を実装する必要があります.
    """

    def parse(self, data: Any) -> Dict[str, Any]:
        """デフォルトのパース実装.

        サブクラスが `parse_root(root)` を実装している場合、それを利用して
        lxml の root 要素からパースを行います。ファイルパスが渡された場合は
        `parse_xml` を使うか、なければ `lxml.etree.parse` で解析します。

        サブクラスが独自の `parse` を実装していればそちらが優先されます。
        """
        # 遅延インポートで依存を限定
        from pathlib import Path

        from lxml import etree

        # サブクラスに parse_root があれば利用する。ここでは必要な `parsed_xbrl` を
        # 構築して `parse_root(root, parsed_xbrl)` として渡す。
        if hasattr(self, "parse_root"):
            xbrl_parser = None
            # Try to obtain XbrlParser from the parser module (allows tests to monkeypatch
            # module-level XbrlParser), otherwise fall back to the packaged edinet_xbrl.
            import importlib

            try:
                mod = importlib.import_module(self.__class__.__module__)
                maybe_cls = getattr(mod, "XbrlParser", None)
                if maybe_cls is not None:
                    cls = maybe_cls
                else:
                    from edinet_xbrl.edinet_xbrl_parser import EdinetXbrlParser

                    cls = EdinetXbrlParser
                xbrl_parser = cls()
            except Exception:
                xbrl_parser = None

            if isinstance(data, etree._Element):
                # create parsed_xbrl from root by writing a temporary file
                if xbrl_parser is None:
                    # cannot build parsed_xbrl without external parser
                    return self.parse_root(data, None)
                import tempfile

                with tempfile.NamedTemporaryFile(mode="wb", suffix=".xbrl", delete=False) as f:
                    f.write(etree.tostring(data, encoding="utf-8"))
                    tmp_path = f.name
                parsed = xbrl_parser.parse_file(tmp_path)
                return self.parse_root(data, parsed)

            if isinstance(data, (str, Path)):
                file_path = str(data)
                if xbrl_parser is not None:
                    parsed = xbrl_parser.parse_file(file_path)
                else:
                    parsed = None
                if hasattr(self, "parse_xml"):
                    root = self.parse_xml(data)
                else:
                    parser = etree.XMLParser(recover=True)
                    tree = etree.parse(str(data), parser=parser)
                    root = tree.getroot()
                return self.parse_root(root, parsed)

        raise NotImplementedError("parse is not implemented for this parser")

    @abstractmethod
    def validate_data(self, data: Any) -> bool:
        """渡されたデータがパーサーの期待する形式か検証する.

        Returns:
            検証に成功すれば True
        """
