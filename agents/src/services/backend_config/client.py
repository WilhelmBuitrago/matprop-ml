"""
REST-based client for the backend configuration service.
This replaces the file-based configuration loading with API calls to the centralized config service.
"""
import httpx
import json
import time
import logging
from typing import Any, Dict, Optional
from threading import Lock, RLock
import os

logger = logging.getLogger(__name__)

class ConfigServiceClient:
    """REST client for the backend configuration service with caching and retry logic."""

    def __init__(self, base_url: str = "http://backend_config:8005", cache_ttl: int = 5):
        """
        Initialize the configuration service client.

        Args:
            base_url: Base URL for the configuration service
            cache_ttl: Cache time-to-live in seconds
        """
        self.base_url = base_url
        self.cache_ttl = cache_ttl
        self._config_cache = None
        self._last_fetch_time = 0
        self._lock = RLock()
        self._client = httpx.Client(timeout=30.0)  # 30 second timeout

    def _fetch_config(self) -> Dict[str, Any]:
        """Fetch configuration from the service with retry logic."""
        with self._lock:
            # Check if we should use cached value
            current_time = time.time()
            if self._config_cache is not None and (current_time - self._last_fetch_time) < self.cache_ttl:
                return self._config_cache

            # Try to fetch config with retries
            retries = 3
            for attempt in range(retries):
                try:
                    response = self._client.get(f"{self.base_url}/config")
                    if response.status_code == 200:
                        config_data = response.json()
                        self._config_cache = config_data
                        self._last_fetch_time = current_time
                        return config_data
                    else:
                        logger.warning(f"Config service returned status {response.status_code}: {response.text}")
                except Exception as e:
                    if attempt == retries - 1:
                        logger.error(f"Failed to fetch config after {retries} attempts: {e}")
                        raise
                    else:
                        logger.warning(f"Failed to fetch config (attempt {attempt + 1}/{retries}): {e}")
                        time.sleep(1)

            # If we get here, all retries failed
            raise ConnectionError(f"Failed to fetch configuration from {self.base_url}/config after {retries} attempts")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by dot notation key.

        Args:
            key: Dot notation key (e.g., "models.embedding.provider")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        try:
            config_data = self._fetch_config()

            # Navigate through nested dict using dot notation
            keys = key.split('.')
            value = config_data
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value
        except Exception as e:
            logger.warning(f"Failed to get config key '{key}': {e}")
            return default

    def get_all(self) -> Dict[str, Any]:
        """Get the entire configuration dictionary."""
        try:
            return self._fetch_config()
        except Exception as e:
            logger.error(f"Failed to get all config: {e}")
            return {}

# Singleton instance
_config_client: Optional[ConfigServiceClient] = None

def get_config_client() -> ConfigServiceClient:
    """Get the singleton configuration client instance."""
    global _config_client
    if _config_client is None:
        _config_client = ConfigServiceClient()
    return _config_client

# For backward compatibility, we'll also create a simple client instance
client = get_config_client()