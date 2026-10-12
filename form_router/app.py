"""
HTTP-слой: страница, каталог форм и классификация. Тикеты не создаются.

  .venv/bin/uvicorn form_router.app:app --port 8000
"""

from __future__ import annotations

import threading
import time
from collections import deque
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from form_router.catalog import load_catalog
from form_router.config import Settings, load_settings
from form_router.service import MAX_TEXT, classify_text

_HTML = Path(__file__).resolve().parent / "static" / "index.html"
_RATE_WINDOW_SEC = 60.0


class ClassifyIn(BaseModel):
    text: str = Field(default="", max_length=MAX_TEXT)
    use_llm: bool = True


class RateLimiter:
    def __init__(self, limit: int, window_sec: float = _RATE_WINDOW_SEC) -> None:
        self._limit = limit
        self._window = window_sec
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            self._evict(now)
            bucket = self._hits.setdefault(key, deque())
            if len(bucket) >= self._limit:
                return False
            bucket.append(now)
            return True

    def _evict(self, now: float) -> None:
        for key in list(self._hits):
            bucket = self._hits[key]
            while bucket and now - bucket[0] > self._window:
                bucket.popleft()
            if not bucket:
                del self._hits[key]


def build_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/form-router", tags=["Form router"])
    catalog = load_catalog(settings.catalog_path)
    limiter = RateLimiter(settings.rate_limit_per_min)

    def cors() -> dict[str, str]:
        if not settings.cors_origin:
            return {}
        return {
            "Access-Control-Allow-Origin": settings.cors_origin,
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "600",
            "Vary": "Origin",
        }

    def client_ip(request: Request) -> str:
        if settings.trust_proxy:
            forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
            if forwarded:
                return forwarded
        return request.client.host if request.client else "unknown"

    @router.get("", include_in_schema=False)
    @router.get("/")
    async def page():
        return FileResponse(_HTML, media_type="text/html; charset=utf-8")

    @router.get("/forms")
    async def forms():
        return JSONResponse(content=catalog, headers=cors())

    @router.options("/forms", include_in_schema=False)
    @router.options("/classify", include_in_schema=False)
    async def preflight():
        return Response(status_code=204, headers=cors())

    @router.post("/classify")
    async def classify(payload: ClassifyIn, request: Request):
        if not limiter.allow(client_ip(request)):
            raise HTTPException(status_code=429, detail="Слишком много запросов", headers=cors())
        result = await run_in_threadpool(
            classify_text, payload.text, settings, use_llm=payload.use_llm
        )
        if result["form"] not in catalog["forms"]:
            result = {**result, "form": "other"}
        return JSONResponse(content=result, headers=cors())

    return router


def create_app(settings: Settings | None = None) -> FastAPI:
    application = FastAPI(
        title="Form Router",
        version="1.0",
        description="Подбор формы обращения в IT Support по тексту проблемы.",
    )
    application.include_router(build_router(settings or load_settings()))

    @application.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse("/form-router/")

    return application


app = create_app()
