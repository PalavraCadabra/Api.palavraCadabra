import logging
import time
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_v1_router
from app.config import settings
from app.core.rate_limit import limiter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("palavracadabra.audit")
logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup: verify DB connection
    from app.database import engine

    async with engine.begin() as conn:
        await conn.execute(
            __import__("sqlalchemy").text("SELECT 1")
        )
    yield
    # Shutdown: dispose engine
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- Rate limiting ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS ---
# In dev, allow any localhost port (Flutter web uses random ports).
# In production, CORS_ALLOW_ALL_LOCALHOST should be False.
_cors_origins: list[str] = list(settings.ALLOWED_ORIGINS)
if settings.CORS_ALLOW_ALL_LOCALHOST:
    _cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=not settings.CORS_ALLOW_ALL_LOCALHOST,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
)


# --- Security Headers Middleware ---
@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:  # type: ignore[type-arg]
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    # Allow Swagger UI and ReDoc CDN resources on docs pages
    path = request.url.path
    if path in ("/docs", "/redoc", "/openapi.json"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' https://fastapi.tiangolo.com data:; "
            "frame-ancestors 'none'"
        )
    else:
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
    return response


# --- Audit Log Middleware ---
@app.middleware("http")
async def audit_log(request: Request, call_next) -> Response:  # type: ignore[type-arg]
    start_time = time.time()
    response: Response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)

    # Extract user_id from JWT if present (best-effort, non-blocking)
    user_id = "anonymous"
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from jose import jwt as jose_jwt

            token = auth_header.split(" ", 1)[1]
            payload = jose_jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM], options={"verify_exp": False}
            )
            user_id = payload.get("sub", "unknown")
        except Exception:
            user_id = "invalid_token"

    client_ip = request.client.host if request.client else "unknown"

    logger.info(
        "API_REQUEST | ip=%s user=%s method=%s path=%s status=%s duration_ms=%s",
        client_ip,
        user_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/setup-db", tags=["admin"])
async def setup_database() -> dict[str, str]:
    """Create all database tables. Safe to call multiple times."""
    from app.database import engine
    from app.models.base import Base
    # Import all models to register them with Base
    from app.models import (  # noqa: F401
        user, aac_profile, board, board_cell, symbol,
        usage_log, care_relationship, literacy_milestone,
        consent, literacy_program, literacy_activity, activity_result,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return {"status": "tables created"}
