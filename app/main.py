from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError

from app.exceptions import (
    AppException,
    app_exception_handler,
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.schemas import HealthResponse
from app.utils.config import get_settings

app = FastAPI(title="Stock Investment Analyzer API")

# 起動時に設定を一度だけ読み込み、アプリ状態に保持
app.state.settings = get_settings()

# 例外ハンドラの登録
app.add_exception_handler(
    AppException,
    app_exception_handler,
)
app.add_exception_handler(
    HTTPException,
    http_exception_handler,
)
app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)
app.add_exception_handler(Exception, general_exception_handler)


@app.get("/health", response_model=HealthResponse)
async def health():
    return {"status": "ok"}


# Include additional routers from app.api when implemented
try:
    from app.api import router as api_router

    app.include_router(api_router, prefix="/api")
except ImportError:
    # `app.api` may not yet be implemented in early project setup;
    # ignore module-not-found errors but let other exceptions surface.
    pass

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
