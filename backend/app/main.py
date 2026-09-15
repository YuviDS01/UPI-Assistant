"""
FastAPI application entrypoint.

This file's only job is composition: create the app, register routers,
register exception handlers, add middleware. It must never contain business
logic — that always lives in services (app/services/) or route handlers
that call services.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import health, users
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import RequestLoggingMiddleware, configure_logging

configure_logging()
logger = logging.getLogger("app.main")
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Agentic UPI Payment Assistant — prototype (non-custodial demo)",
    version="0.1.0",
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(health.router)
app.include_router(users.router)


@app.exception_handler(AppException)
def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
    """
    Single place that turns a domain exception into an HTTP response.
    Services/tools raise AppException subclasses without knowing about
    HTTP at all — this is the only file that maps error_code -> status_code.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "message": exc.message, "detail": exc.detail},
    )


@app.exception_handler(Exception)
def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    """
    Last-resort handler. Logs the full traceback server-side but never
    leaks internals (stack trace, SQL, file paths) to the client — the
    client only ever sees a generic message and an error_code they can
    quote back to us.
    """
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"error_code": "INTERNAL_ERROR", "message": "Something went wrong.", "detail": {}},
    )
