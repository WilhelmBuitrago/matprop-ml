from __future__ import annotations


class SearchScientificDocumentsError(Exception):
    """Base exception for search scientific documents workflow."""


class ProviderFailureError(SearchScientificDocumentsError):
    """Raised when all configured providers fail."""


class NormalizationError(SearchScientificDocumentsError):
    """Raised when a raw provider payload cannot be normalized."""
