"""
FastAPI application entrypoint.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import approvals, chat, health, mandates, payments, users, webhooks
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.services.scheduler_service import start_scheduler, stop_scheduler
from app.workers.payment_scheduler import process_due_mandates

configure_logging()
logger = logging.getLogger("app.main")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.enable_scheduler:
        start_scheduler(process_due_mandates, settings.scheduler_interval_seconds)
        logger.info(f"Scheduler started (every {settings.scheduler_interval_seconds}s).")
    yield
    if settings.enable_scheduler:
        stop_scheduler()


app = FastAPI(
    title=settings.app_name,
    description="Agentic UPI Payment Assistant — prototype (non-custodial demo)",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(RequestLoggingMiddleware)
# Dev-only CORS: allows the Vite dev server to call this API from the
# browser. Deliberately narrow (named origins, not "*") even in a
# prototype — "*" combined with credentialed requests is a bad habit to
# build even here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.include_router(health.router)
app.include_router(users.router)
app.include_router(approvals.router)
app.include_router(mandates.router)
app.include_router(payments.router)
app.include_router(chat.router)
app.include_router(webhooks.router)



@app.exception_handler(AppException)
def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "message": exc.message, "detail": exc.detail},
    )


@app.exception_handler(Exception)
def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"error_code": "INTERNAL_ERROR", "message": "Something went wrong.", "detail": {}},
    )