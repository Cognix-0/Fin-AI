"""
Consistent error handling.

Every error response uses the same envelope:
    {"success": false, "error": {"code": "...", "message": "...", "fields": [...]?}}
"""
import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


class AppError(HTTPException):
    """HTTPException with a machine-readable code."""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(status_code=status_code, detail={"code": code, "message": message})


def not_found(what: str = "Resource") -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"{what} not found")


def forbidden(message: str = "You do not have permission to perform this action") -> AppError:
    return AppError(status.HTTP_403_FORBIDDEN, "INSUFFICIENT_PERMISSIONS", message)


def conflict(code: str, message: str) -> AppError:
    return AppError(status.HTTP_409_CONFLICT, code, message)


def bad_request(code: str, message: str) -> AppError:
    return AppError(status.HTTP_400_BAD_REQUEST, code, message)


_DEFAULT_CODES = {
    400: "BAD_REQUEST",
    401: "NOT_AUTHENTICATED",
    403: "INSUFFICIENT_PERMISSIONS",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    429: "TOO_MANY_REQUESTS",
}


def _envelope(code: str, message: str, **extra) -> dict:
    return {"success": False, "error": {"code": code, "message": message, **extra}}


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        body = _envelope(detail["code"], detail.get("message", ""))
    else:
        body = _envelope(_DEFAULT_CODES.get(exc.status_code, "ERROR"), str(detail))
    return JSONResponse(status_code=exc.status_code, content=body, headers=getattr(exc, "headers", None))


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    fields = []
    for err in exc.errors():
        loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
        msg = err.get("msg", "Invalid value")
        # Pydantic prefixes custom validator messages with "Value error, "
        msg = msg.removeprefix("Value error, ")
        fields.append({"field": ".".join(loc), "message": msg})
    first = fields[0] if fields else {"field": "", "message": "Invalid request"}
    message = f"{first['field']}: {first['message']}" if first["field"] else first["message"]
    return JSONResponse(
        status_code=422,
        content=_envelope("VALIDATION_ERROR", message, fields=fields),
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s", request.method, request.url.path, exc_info=exc)
    message = "An unexpected error occurred" if settings.is_production else str(exc)
    return JSONResponse(status_code=500, content=_envelope("INTERNAL_ERROR", message))


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
