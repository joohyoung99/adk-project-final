import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from app.api.routes import health, query
from app.api.executor import ADKAgentExecutor

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
UI_DIST_DIR = Path(__file__).resolve().parents[2] / "ui" / "dist"


def _parse_allowed_origins() -> list[str]:
    raw = (os.getenv("ALLOWED_ORIGINS") or "").strip()
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: 에이전트 실행기 초기화
    app.state.executor = ADKAgentExecutor()
    yield
    # Shutdown: 정리 작업


def create_app() -> FastAPI:
    app = FastAPI(
        title="ADK RAG API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    allowed_origins = _parse_allowed_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )

    # 라우터 등록
    app.include_router(health.router)
    app.include_router(query.router, prefix="/v1")

    if UI_DIST_DIR.exists():
        app.mount("/", StaticFiles(directory=str(UI_DIST_DIR), html=True), name="ui")
    else:
        logging.warning("UI dist directory not found at %s; serving API only.", UI_DIST_DIR)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8080")),
        workers=int(os.getenv("UVICORN_WORKERS", "1")),
        reload=os.getenv("ENV", "dev") == "dev",
    )
