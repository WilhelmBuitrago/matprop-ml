from __future__ import annotations


class ValidateMaterialConstraintsError(Exception):
    """Base exception for constraint validation tool errors."""


class ConstraintValidationError(ValidateMaterialConstraintsError):
    """Raised when constraints are malformed or logically invalid."""
