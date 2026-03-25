from __future__ import annotations


class QueryMaterialsError(Exception):
    """Base exception for query materials tool errors."""


class QueryValidationError(QueryMaterialsError):
    """Raised when runtime validation fails."""


class QueryAPIError(QueryMaterialsError):
    """Raised when Materials Project API calls fail."""
