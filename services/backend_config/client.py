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
    
    def __init__(self, base_url: str = "http://backend_config:8004", cache_ttl: int = 5):
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
 
           # Try to fetch config with retries
            retries = 3
            for attempt in range(retries):
                try:
                    response = self._client.get(f"{self.base_url}/config")
                    if response.status_code == 200:
                        return response.json()
                    else:
                        logger.warning(f"Config service returned status {response.status_code}: {response.text}")
                except Exception as e:
                    if attempt == retries - 1:
                        logger.error(f"Failed to fetch config after {retries} attempts: {e}")
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed, retrying: {e}")
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
            
            # If we get here, all retries failed
            raise Exception("Failed to fetch configuration from service")
    
    def _is_cache_expired(self) -> bool:
        """Check if the configuration cache has expired."""
        return time.time() - self._last_fetch_time > self.cache_ttl
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the current configuration with caching.
        
        Returns:
            Dict: The current configuration
        """
        with self._lock:
            if self._config_cache is None or self._is_cache_expired():
                self._config_cache = self._fetch_config()
                self._last_fetch_time = time.time()
            return self._config_cache
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            path: Dot-separated path to the configuration value (e.g., "models.default")
            default: Default value if the path doesn't exist
            
        Returns:
            The configuration value or default
        """
        config = self.get_config()
        keys = path.split('.')
        value = config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

# Create a global instance
_config_client: Optional[ConfigServiceClient] = None

def get_config_client() -> ConfigServiceClient:
    """Get the singleton configuration client instance."""
    global _config_client
    if _config_client is None:
        _config_client = ConfigServiceClient()
    return _config_client

# For backward compatibility, we'll also create a simple client instance
client = get_config_client()