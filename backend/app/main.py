import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.admin_router import router as admin_router
from app.api.router import router
from app.core.config import get_settings
from app.core.database import dispose_engines, get_app_engine
from app.core.errors import AppError
from app.core.logging import configure_logging
from app.core.security import mask_secret
from app.schemas.common import HealthResponse
from app.services.query_service import QueryService

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    del app
    startup_extra: dict[str, Any] = {
        "event": "service.startup",
        "app_env": settings.app_env,
        "model_mode": settings.default_model_config,
    }
    if settings.real_model_name:
        startup_extra.update(
            {
                "provider": "openai_compatible",
                "model": settings.real_model_name,
                "protocol": settings.real_model_protocol,
                "api_key_mask": mask_secret(
                    settings.real_model_api_key.get_secret_value()
                    if settings.real_model_api_key
                    else None
                ),
            }
        )
    logger.info("service starting", extra=startup_extra)
    if settings.app_env in ("demo", "prod"):
        await asyncio.to_thread(_warm_rag_embedding)
    if settings.app_env != "test":
        await asyncio.to_thread(_recover_stale_executions)
    yield
    dispose_engines()


def _recover_stale_executions() -> None:
    from app.core.database import new_session

    with new_session() as db:
        service = QueryService(db, settings)
        discovered, claimed = service.recover_available(settings.execution_recovery_batch_size)
        logger.info(
            "bounded execution recovery completed",
            extra={
                "event": "graph.recovery_scan",
                "discovered": discovered,
                "claimed": claimed,
                "limit": settings.execution_recovery_batch_size,
            },
        )


def _warm_rag_embedding() -> None:
    from app.text2sql.rag import BgeEmbeddingProvider

    started = datetime.now(UTC)
    BgeEmbeddingProvider(settings.rag_embedding_model).encode(["经管之星检索预热"])
    logger.info(
        "rag embedding model warmed",
        extra={
            "event": "rag.embedding_warmup",
            "model": settings.rag_embedding_model,
            "duration_ms": int((datetime.now(UTC) - started).total_seconds() * 1000),
        },
    )


app = FastAPI(
    title="经管之星 API",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Idempotency-Key", "Last-Event-ID", "X-Request-ID"],
    expose_headers=["X-Request-ID", "Content-Disposition"],
)
app.include_router(router)
app.include_router(admin_router)


@app.middleware("http")
async def request_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex}"
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


def error_payload(
    request: Request,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "requestId": getattr(request.state, "request_id", f"req_{uuid4().hex}"),
            "details": details,
        }
    }


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(request, exc.code, exc.message, exc.details),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = {
        "errors": [
            {"loc": ".".join(str(item) for item in error["loc"]), "message": error["msg"]}
            for error in exc.errors()
        ]
    }
    return JSONResponse(
        status_code=422, content=error_payload(request, "VALIDATION_ERROR", "请求参数错误", details)
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled request error",
        extra={"event": "http.unhandled", "request_id": getattr(request.state, "request_id", None)},
    )
    return JSONResponse(
        status_code=500, content=error_payload(request, "INTERNAL_ERROR", "服务内部错误")
    )


@app.get("/health/live", response_model=HealthResponse)
def liveness() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        timestamp=datetime.now(UTC),
        checks={"process": "ok"},
    )


@app.get("/health/ready", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
def readiness() -> JSONResponse | HealthResponse:
    try:
        with get_app_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        payload = HealthResponse(
            status="unavailable",
            version=settings.app_version,
            timestamp=datetime.now(UTC),
            checks={"database": "unavailable"},
        )
        return JSONResponse(status_code=503, content=payload.model_dump(mode="json", by_alias=True))
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        timestamp=datetime.now(UTC),
        checks={"database": "ok"},
    )
