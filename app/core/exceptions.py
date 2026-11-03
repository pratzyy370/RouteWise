"""
Application-specific exception hierarchy.

Every exception carries a ``status_code`` (HTTP) and ``detail`` message so
that error-handling middleware can produce a uniform JSON response.
"""

from __future__ import annotations


class RouteWiseError(Exception):
    """Base exception for all RouteWise application errors."""

    status_code: int = 500
    detail: str = "An unexpected error occurred"

    def __init__(
        self,
        detail: str | None = None,
        status_code: int | None = None,
    ) -> None:
        if detail is not None:
            self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.detail)


class NotFoundError(RouteWiseError):
    """Requested resource does not exist."""

    status_code: int = 404
    detail: str = "Resource not found"


class AuthenticationError(RouteWiseError):
    """Caller could not be authenticated."""

    status_code: int = 401
    detail: str = "Authentication failed"


class AuthorizationError(RouteWiseError):
    """Caller lacks permission for the requested action."""

    status_code: int = 403
    detail: str = "Permission denied"


class ValidationError(RouteWiseError):
    """Input validation failed."""

    status_code: int = 422
    detail: str = "Validation error"


class ProviderError(RouteWiseError):
    """An external mobility provider returned an error.

    Attributes:
        provider_name: Identifier of the provider that failed (e.g. "uber").
    """

    status_code: int = 502
    detail: str = "Provider error"

    def __init__(
        self,
        provider_name: str,
        detail: str | None = None,
        status_code: int | None = None,
    ) -> None:
        self.provider_name = provider_name
        super().__init__(
            detail=detail or f"Provider '{provider_name}' returned an error",
            status_code=status_code,
        )


class ProviderTimeoutError(ProviderError):
    """An external mobility provider request timed out."""

    status_code: int = 504
    detail: str = "Provider request timed out"

    def __init__(
        self,
        provider_name: str,
        detail: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(
            provider_name=provider_name,
            detail=detail or f"Provider '{provider_name}' request timed out",
            status_code=status_code,
        )


class RateLimitError(RouteWiseError):
    """Caller has exceeded the allowed request rate."""

    status_code: int = 429
    detail: str = "Rate limit exceeded"


class InsufficientDataError(RouteWiseError):
    """Not enough data is available to fulfil the request."""

    status_code: int = 422
    detail: str = "Insufficient data to process request"
