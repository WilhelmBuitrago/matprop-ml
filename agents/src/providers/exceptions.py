"""Custom exception hierarchy for LLM provider errors."""
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    
    def __init__(self, message: str, provider: str = None, model: str = None, 
                 details: Dict[str, Any] = None):
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.details = details or {}
        logger.debug("LLMProviderError created: %s (provider=%s, model=%s)", 
                    message, provider, model)


class ProviderTimeoutError(LLMProviderError):
    """Raised when provider request times out."""
    
    def __init__(self, message: str, provider: str = None, model: str = None,
                 timeout_seconds: float = None):
        super().__init__(message, provider, model)
        self.timeout_seconds = timeout_seconds


class ProviderAPIError(LLMProviderError):
    """Raised when provider returns API error (rate limit, auth, etc)."""
    
    def __init__(self, message: str, provider: str = None, model: str = None,
                 status_code: int = None, error_details: str = None):
        super().__init__(message, provider, model)
        self.status_code = status_code
        self.error_details = error_details


class ProviderConnectionError(LLMProviderError):
    """Raised when provider connection fails."""
    
    def __init__(self, message: str, provider: str = None, model: str = None,
                 connection_error: str = None):
        super().__init__(message, provider, model)
        self.connection_error = connection_error


class ProviderAuthenticationError(ProviderAPIError):
    """Raised when provider authentication fails."""
    
    def __init__(self, message: str, provider: str = None, model: str = None,
                 auth_error: str = None):
        super().__init__(message, provider, model)
        self.auth_error = auth_error


class ProviderQuotaExceededError(ProviderAPIError):
    """Raised when provider quota/limit is exceeded."""
    
    def __init__(self, message: str, provider: str = None, model: str = None,
                 quota_limit: str = None):
        super().__init__(message, provider, model)
        self.quota_limit = quota_limit