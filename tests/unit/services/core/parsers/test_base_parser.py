from __future__ import annotations

from typing import Any, Dict

from app.services.core.parsers.base_parser import BaseParser


class DummyParser(BaseParser):
    def parse(self, data: Any) -> Dict[str, Any]:
        return {"ok": True, "data": data}

    def validate_data(self, data: Any) -> bool:
        return data is not None


def test_dummy_parser_parse_and_validate():
    p = DummyParser()
    assert p.validate_data("something") is True
    res = p.parse("something")
    assert res["ok"] is True

    # validate None -> False
    assert p.validate_data(None) is False
