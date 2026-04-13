"""API middleware and exception handlers."""

import logging
import traceback
import uuid

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.application.errors import ApplicationError
from src.presentation.schemas import ApiErrorPayload, ApiErrorResponse

logger = logging.getLogger(__name__)

# Constants
REQUEST_ID_HEADER = "X-Request-Id"
REQUEST_ID_STATE_KEY = "request_id"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware that generates and attaches a unique request ID to each request.

    The request ID is:
    - Stored in request.state for access by handlers
    - Returned in the X-Request-Id response header
    - Included in all error responses for correlation
    """

    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Store in request state for access by handlers
        request.state.request_id = request_id

        # Process the request
        response = await call_next(request)

        # Add request ID to response header
        response.headers[REQUEST_ID_HEADER] = request_id

        return response


def get_request_id(request: Request) -> str:
    """Extract request ID from request state.

    Args:
        request: The FastAPI request object

    Returns:
        The request ID string, or "unknown" if not set
    """
    return getattr(request.state, REQUEST_ID_STATE_KEY, "unknown")


def _build_error_payload(
    code: str,
    message: str,
    request_id: str,
    details: dict | None = None,
    fields: dict[str, list[str]] | None = None,
    retryable: bool = False,
) -> dict:
    """Build standardized error payload dictionary."""
    payload = ApiErrorPayload(
        code=code,
        message=message,
        request_id=request_id,
        retryable=retryable,
    )
    if details:
        payload.details = details
    if fields:
        payload.fields = fields
    return ApiErrorResponse(error=payload).model_dump()


def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    """Handle ApplicationError exceptions.

    Uses the error's http_status, code, message, and details from the exception.
    Always includes request_id in the response.
    Logs 4xx errors as WARNING and 5xx errors as ERROR with full context.
    """
    request_id = get_request_id(request)

    # Get error details from exception
    error_data = exc.to_dict()
    error_code = error_data.get("code", "application_error")
    error_message = error_data.get("message", "Внутренняя ошибка сервера")
    details = error_data.get("details")
    fields = error_data.get("fields")

    # Log with appropriate level based on HTTP status
    # 4xx = client errors (WARNING), 5xx = server errors (ERROR)
    if exc.http_status >= 500:
        logger.error(
            f"Application error: {error_code}",
            extra={
                "request_id": request_id,
                "error_code": error_code,
                "error_message": error_message,
                "details": details,
                "fields": fields,
                "http_status": exc.http_status,
            },
        )
    else:
        logger.warning(
            f"Client error: {error_code}",
            extra={
                "request_id": request_id,
                "error_code": error_code,
                "http_status": exc.http_status,
            },
        )

    payload = _build_error_payload(
        code=error_code,
        message=error_message,
        request_id=request_id,
        details=details,
        fields=fields,
        retryable=error_data.get("retryable", False),
    )

    return JSONResponse(
        status_code=exc.http_status,
        content=payload,
    )


def _parse_validation_errors(errors: list[dict]) -> dict[str, list[str]]:
    """Parse FastAPI validation errors into field-level error map.

    Args:
        errors: List of error dictionaries from FastAPI validation

    Returns:
        Dictionary mapping field names to lists of error messages
    """
    fields: dict[str, list[str]] = {}

    for error in errors:
        # Extract location (field path)
        loc = error.get("loc", [])
        if len(loc) >= 1:
            # Build field path string (e.g., "body.title" or "query.page")
            field_path = ".".join(str(x) for x in loc)
        else:
            field_path = "general"

        # Get error message
        msg = error.get("msg", "Ошибка валидации")

        # Add to fields map
        if field_path not in fields:
            fields[field_path] = []
        fields[field_path].append(msg)

    return fields


def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI RequestValidationError.

    Maps validation errors to field-level error format with code="validation_error".
    Includes request_id and parsed field errors.
    """
    request_id = get_request_id(request)

    # Parse field-level errors from FastAPI error format
    fields = _parse_validation_errors(exc.errors())

    # Build error count message
    error_count = len(exc.errors())
    if error_count == 1:
        message = "Ошибка валидации поля"
    else:
        message = f"Ошибки валидации в {len(fields)} полях"

    payload = _build_error_payload(
        code="validation_error",
        message=message,
        request_id=request_id,
        fields=fields if fields else None,
        retryable=False,
    )

    return JSONResponse(
        status_code=422,
        content=payload,
    )


def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPException.

    Wraps the HTTPException in standardized ApiErrorResponse format.
    Includes request_id for correlation.
    """
    request_id = get_request_id(request)

    # Map status code to error code
    status_to_code = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        422: "unprocessable_entity",
        429: "rate_limited",
        500: "internal_error",
        502: "bad_gateway",
        503: "service_unavailable",
    }

    code = status_to_code.get(exc.status_code, f"http_{exc.status_code}")

    # Get message from detail
    message = str(exc.detail) if exc.detail else "Ошибка запроса"

    payload = _build_error_payload(
        code=code,
        message=message,
        request_id=request_id,
        retryable=exc.status_code >= 500,  # Server errors might be retryable
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=payload,
    )


def fallback_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle any unhandled Exception.

    Logs the full stack trace for debugging but returns a safe generic
    error message to the client. Always returns 500 status.
    """
    request_id = get_request_id(request)

    # Log full exception details with stack trace using structured logging
    logger.exception(
        f"Unhandled exception: {type(exc).__name__}",
        extra={
            "request_id": request_id,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        },
    )

    # Return safe generic error (don't leak internal details)
    payload = _build_error_payload(
        code="internal_error",
        message="Внутренняя ошибка сервера",
        request_id=request_id,
        retryable=False,
    )

    return JSONResponse(
        status_code=500,
        content=payload,
    )
