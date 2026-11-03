"""
Global exception handlers for RouteWise.
"""

import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import RouteWiseError

logger = logging.getLogger(__name__)


async def routewise_error_handler(request: Request, exc: RouteWiseError) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None)
    logger.warning("RouteWiseError on %s: %s (status=%d)", request.url.path, exc.detail, exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_type": type(exc).__name__,
            "request_id": req_id,
        },
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "error_type": "ValidationError",
            "request_id": req_id,
        },
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None)
    logger.exception("Unhandled server exception on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred. Please try again later.",
            "error_type": "InternalServerError",
            "request_id": req_id,
        },
    )
