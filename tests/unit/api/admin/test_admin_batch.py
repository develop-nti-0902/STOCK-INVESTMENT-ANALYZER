"""管理用バッチページのルートとテンプレート表示の単体テスト."""

from types import SimpleNamespace

import pytest
from fastapi.responses import HTMLResponse

import app.api.admin.batch as batch_mod
import app.templates_config as templates_config


@pytest.mark.asyncio
async def test_admin_batch_route_registered() -> None:
    """`/admin/batch` がルーターに登録されていることを確認する."""
    routes = [r for r in batch_mod.router.routes if getattr(r, "path", None) == "/admin/batch"]
    assert len(routes) == 1
    route = routes[0]
    assert "GET" in route.methods
    assert route.response_class is HTMLResponse


@pytest.mark.asyncio
async def test_admin_batch_page_returns_template_response(monkeypatch) -> None:
    """テンプレートレンダリング呼び出しが適切に行われることを確認する."""
    captured: dict = {}

    def dummy_template_response(name, context):
        captured["name"] = name
        captured["context"] = context
        return "dummy-response"

    monkeypatch.setattr(templates_config.templates, "TemplateResponse", dummy_template_response)

    fake_request = SimpleNamespace()
    result = await batch_mod.batch_page(fake_request)

    assert result == "dummy-response"
    assert captured["name"] == "admin/batch_trigger.html"
    assert isinstance(captured["context"], dict)
    assert captured["context"]["request"] is fake_request
