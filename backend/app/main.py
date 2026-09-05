import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
import redis

from app.core.config import settings
from app.core.errors import AppError
from app.core.database import engine
from app.api import stocks, watchlist, profile, auth, onboarding
from app.jobs.market_poll import start_scheduler

logger = logging.getLogger("app")

app = FastAPI(title="Smart Watchlist API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(onboarding.router)
app.include_router(stocks.router)
app.include_router(watchlist.router)
app.include_router(profile.router)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """
    AppError.detail is already {"error": {"code": ..., "message": ...}}.
    Returning it directly avoids FastAPI's default HTTPException behavior,
    which would nest it under a top-level "detail" key.
    """
    return JSONResponse(status_code=exc.status_code, content=exc.detail)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Keep request-validation failures in the same error envelope as everything else."""
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors(),
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all: log the real error server-side, never leak internals to the client."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}},
    )


_scheduler = None

@app.on_event("startup")
def on_startup():
    global _scheduler
    _scheduler = start_scheduler()

@app.on_event("shutdown")
def on_shutdown():
    if _scheduler:
        _scheduler.shutdown(wait=False)

@app.get("/health")
def health(response_status_code: int = 200):
    """
    Honest health check: reuses the app's existing engine (no per-request
    engine creation), and returns 503 if any required dependency is down
    rather than always claiming 'ok'.
    """
    components = {"database": "healthy", "redis": "healthy"}
    healthy = True

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        components["database"] = "unhealthy"
        healthy = False

    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
    except Exception:
        components["redis"] = "unhealthy"
        healthy = False

    status_code = 200 if healthy else 503
    body = {"status": "healthy" if healthy else "unhealthy", "components": components}
    return JSONResponse(status_code=status_code, content=body)
