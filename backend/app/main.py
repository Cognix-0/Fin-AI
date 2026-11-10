import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.middleware import RequestContextMiddleware
from app.db.session import check_db_connection, engine
from app.services.receipt_storage import ReceiptStorage

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO if not settings.is_production else logging.WARNING,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ReceiptStorage().ensure_root()
    logger.info("%s %s starting (%s)", settings.app_name, settings.app_version, settings.environment)
    yield
    await engine.dispose()


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)

# ── Middleware (last added runs first) ────────────────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,      # Required for cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    expose_headers=["X-Request-ID", "Content-Disposition"],
)
app.add_middleware(RequestContextMiddleware)

register_exception_handlers(app)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix=settings.api_prefix)


# ── Health endpoints ──────────────────────────────────────────────────────────
@app.get(f"{settings.api_prefix}/health", tags=["Health"])
async def health():
    """Overall status, including database connectivity."""
    db_ok = await check_db_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
        "version": settings.app_version,
    }


@app.get(f"{settings.api_prefix}/health/live", tags=["Health"])
async def liveness():
    """Liveness probe: the process is up. Never touches the database."""
    return {"status": "ok"}


@app.get(f"{settings.api_prefix}/health/ready", tags=["Health"])
async def readiness():
    """Readiness probe: 503 until the database is reachable, so traffic isn't routed too early."""
    if await check_db_connection():
        return {"status": "ready"}
    return JSONResponse(status_code=503, content={"status": "not_ready", "database": "unreachable"})
