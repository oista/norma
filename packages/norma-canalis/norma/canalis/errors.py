"""Canalis error hierarchy."""

from __future__ import annotations


class CanalisError(Exception):
    """Base error for norma-canalis."""


class ConnectError(CanalisError):
    """Failed to establish a connection."""


class AuthError(CanalisError):
    """Authentication or authorization failed."""


class NotFoundError(CanalisError):
    """Requested resource was not found."""


class RateLimited(CanalisError):
    """Upstream rate limit hit; may carry retry_after seconds."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class TransientError(CanalisError):
    """Temporary failure; safe to retry."""


class PermanentError(CanalisError):
    """Non-retryable failure."""


class DriverUnavailable(CanalisError):
    """Driver dependency missing; install the matching extra."""
