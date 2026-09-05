"""InvoiceFlow FastAPI application. Fictional portfolio demonstration."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, demo, health, invoices, metrics, vendors
from app.core.config import get_settings
from app.core.errors import AppError, error_body
from app.core.logging import configure_logging, redact
from app.db.session import get_session_factory, init_db
from app.seed.runner import seed_database


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    await init_db()
    if settings.seed_on_startup:
        factory = get_session_factory()
        async with factory() as session:
            await seed_database(session)
            await session.commit()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="InvoiceFlow API",
        version="1.0.0",
        description="Fictional accounts-payable automation API. No real accounting, email, or bank provider is contacted.",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.cors_origins == "*" else [o.strip() for o in settings.cors_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    hits: dict[str, deque[float]] = defaultdict(deque)

    @application.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or f"req_{uuid4().hex[:12]}"
        ip = request.client.host if request.client else "local"
        now = time.time()
        bucket = hits[ip]
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= settings.rate_limit_per_minute:
            return JSONResponse(
                status_code=429,
                content=error_body(
                    code="RATE_LIMITED", message="Too many requests from this client.", request_id=request_id
                ),
                headers={"X-Request-ID": request_id},
            )
        bucket.append(now)
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-InvoiceFlow"] = "demo-sandbox"
        return response

    @application.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "req_unknown")
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(
                code=exc.code,
                message=redact(exc.message),
                request_id=request_id,
                field_errors=exc.field_errors,
            ),
            headers={"X-Request-ID": request_id},
        )

    application.include_router(health.router)
    application.include_router(auth.router)
    application.include_router(invoices.router)
    application.include_router(vendors.router)
    application.include_router(metrics.router)
    application.include_router(demo.router)

    @application.get("/")
    async def root() -> dict[str, Any]:
        return {
            "service": "invoiceflow-api",
            "demo": True,
            "docs": "/docs",
            "health": "/health",
            "note": "Fictional portfolio demonstration. Browser walkthrough does not require this process.",
        }

    return application


app = create_app()
