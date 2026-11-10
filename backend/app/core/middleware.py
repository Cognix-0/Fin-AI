"""HTTP middleware: request IDs, access logging and security headers."""
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("app.access")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Tags every request with an ID, logs method/path/status/duration and adds security headers."""

    async def dispatch(self, request: Request, call_next):
        # Accept an upstream ID (e.g. from a load balancer) if it looks sane
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if 0 < len(incoming) <= 64 else uuid.uuid4().hex
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = request_id
        for key, value in SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)

        # Skip health probes to keep logs readable
        if not request.url.path.endswith("/health") and "/health/" not in request.url.path:
            logger.info(
                "%s %s -> %s (%.1f ms) [%s]",
                request.method, request.url.path, response.status_code, duration_ms, request_id,
            )
        return response
