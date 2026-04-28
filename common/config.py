"""
Centralized configuration loader for the system.
This module provides a singleton-like interface to access configuration,
replacing the dependency on environment variables.
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional, Any
from threading import Lock
import os

# Import the configuration schema and persistence
from services.config_service.config_schema import ConfigSchema
from services.config_service.config_persistence import ConfigPersistence

logger = logging.getLogger(__name__)

class ConfigLoader:
    """Singleton-like configuration loader with caching capabilities."""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self._config: Optional[ConfigSchema] = None
        self._last_load_time: float = 0
        self._cache_ttl: int = 5  # Cache TTL in seconds
        
        # Use absolute path for config directory
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config_store")
        self._persistence = ConfigPersistence(config_dir)
        
        # Initial load
        self.reload()
    
    def _load_from_persistence(self) -> Optional[ConfigSchema]:
        """Load configuration from the persistence layer."""
        try:
            return self._persistence.load_config()
        except Exception as e:
            logger.error(f"Failed to load config from persistence: {e}")
            return None
    
    def reload(self) -> bool:
        """
        Reload configuration from disk.
        
        Returns:
            bool: True if reload was successful, False otherwise
        """
        try:
            config = self._load_from_persistence()
            if config is not None:
                self._config = config
                self._last_load_time = time.time()
                logger.info("Configuration reloaded successfully")
                return True
            else:
                logger.warning("No configuration found in persistence")
                return False
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            return False
    
    def _is_cache_expired(self) -> bool:
        """Check if the configuration cache has expired."""
        return time.time() - self._last_load_time > self._cache_ttl
    
    def get_config(self) -> ConfigSchema:
        """
        Get the current configuration with caching.
        
        Returns:
            ConfigSchema: The current configuration
        """
        if self._config is None or self._is_cache_expired():
            self.reload()
        
        if self._config is None:
            # Return a default configuration if none is loaded
            logger.warning("Returning default configuration as no persisted config was found")
            self._config = ConfigSchema()
            self._last_load_time = time.time()
            
        return self._config
    
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
        value = config.dict()
        
        try:
            for key in keys:
                value = value[key]
            return value
        except KeyError:
            return default


# Create a global instance
_config_loader: Optional[ConfigLoader] = None

def get_config_loader() -> ConfigLoader:
    """Get the singleton configuration loader instance."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader

# Create the default instance
config = get_config_loader()