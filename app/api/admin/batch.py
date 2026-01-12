"""バッチ実行管理画面のルーター."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.templates_config import templates

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/batch", response_class=HTMLResponse)
async def batch_page(request: Request) -> HTMLResponse:
    """バッチ実行管理画面を表示する.

    Args:
        request: FastAPIのRequestオブジェクト

    Returns:
        HTMLResponse: レンダリングされたHTMLテンプレート
    """
    return templates.TemplateResponse(
        "admin/batch_trigger.html",
        {"request": request},
    )
