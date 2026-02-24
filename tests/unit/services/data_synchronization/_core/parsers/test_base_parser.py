"""Unit tests for parser base utilities."""

from __future__ import annotations

from typing import Any, Dict

from app.services.data_synchronization._core.parsers.base_parser import BaseParser


class DummyParser(BaseParser):
    """Simple parser implementation for testing."""

    def parse(self, data: Any) -> Dict[str, Any]:
        """Return parsed payload containing the original data."""
        return {"ok": True, "data": data}

    def validate_data(self, data: Any) -> bool:
        """Validate that data is not None."""
        return data is not None


def test_dummy_parser_parse_and_validate():
    """Parse and validate using DummyParser."""
    p = DummyParser()
    assert p.validate_data("something") is True
    res = p.parse("something")
    assert res["ok"] is True

    # validate None -> False
    assert p.validate_data(None) is False
