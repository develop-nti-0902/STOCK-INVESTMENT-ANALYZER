from fastapi import FastAPI

from app.schemas import HealthResponse

app = FastAPI(title="Stock Investment Analyzer API")


@app.get("/health", response_model=HealthResponse)
async def health():
    return {"status": "ok"}


# Include additional routers from app.api when implemented
try:
    from app.api import router as api_router

    app.include_router(api_router, prefix="/api")
except Exception:
    pass

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
