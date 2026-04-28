from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from enum import Enum
import re


class ModelProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    OLLAMA = "ollama"
    TOGETHER = "together"


class ModelConfig(BaseModel):
    provider: ModelProvider
    model_name: str
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature (0.0 to 2.0)")
    max_tokens: int = Field(default=1000, ge=1, le=4096, description="Maximum tokens to generate")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Nucleus sampling (0.0 to 1.0)")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty (-2.0 to 2.0)")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty (-2.0 to 2.0)")
    api_key: Optional[str] = None
    base_url: Optional[str] = None

    @field_validator('model_name')
    def validate_model_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Model name cannot be empty')
        return v.strip()


class APIConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    debug: bool = False
    cors_origins: List[str] = ["*"]
    rate_limit: int = Field(default=100, ge=1)

    @field_validator('host')
    def validate_host(cls, v):
        # Basic host validation
        if not v or not isinstance(v, str):
            raise ValueError('Host must be a valid string')
        return v


class ExternalAPIConfig(BaseModel):
    """Configuration for external API credentials and settings"""
    
    # Materials Project API
    mp_api_key: Optional[str] = Field(None, description="Materials Project API key")
    
    # Semantic Scholar API
    semantic_scholar_api_key: Optional[str] = Field(None, description="Semantic Scholar API key")
    
    # Crossref API
    crossref_email: Optional[str] = Field(None, description="Email for Crossref API access")
    
    # Unpaywall API
    unpaywall_email: Optional[str] = Field(None, description="Email for Unpaywall API access")
    
    # OpenRouter API
    openrouter_api_key: Optional[str] = Field(None, description="OpenRouter API key")
    
    # Agent API security
    agent_api_key: Optional[str] = Field(None, description="Agent service API key")
    
    # Add validation for API key formats
    @field_validator('mp_api_key')
    @classmethod
    def validate_mp_api_key(cls, v):
        if v is not None and not re.match(r'^[a-zA-Z0-9_-]{20,}$', v):
            raise ValueError('Invalid Materials Project API key format')
        return v
    
    @field_validator('semantic_scholar_api_key')
    @classmethod
    def validate_semantic_scholar_api_key(cls, v):
        if v is not None and not re.match(r'^[a-zA-Z0-9]{8,}$', v):
            raise ValueError('Invalid Semantic Scholar API key format')
        return v
    
    @field_validator('openrouter_api_key')
    @classmethod
    def validate_openrouter_api_key(cls, v):
        if v is not None and not re.match(r'^sk-or-[a-zA-Z0-9]{20,}$', v):
            raise ValueError('Invalid OpenRouter API key format')
        return v


class SystemConfig(BaseModel):
    log_level: str = "INFO"
    data_dir: str = "./data"
    temp_dir: str = "./temp"
    backup_dir: str = "./backups"
    max_workers: int = Field(default=4, ge=1, le=32)
    timeout: int = Field(default=30, ge=1, le=300)
    extra_config: Dict[str, Any] = {}

    @field_validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v not in valid_levels:
            raise ValueError(f'Log level must be one of {valid_levels}')
        return v


class ConfigSchema(BaseModel):
    """Centralized configuration schema for the entire system"""
    
    # Model configurations
    models: Dict[str, ModelConfig] = {}
    
    # API configurations
    api: APIConfig = APIConfig()
    
    # External API configurations
    external_apis: ExternalAPIConfig = ExternalAPIConfig()
    
    # System configurations
    system: SystemConfig = SystemConfig()
    
    # Additional configuration fields can be added here
    # This is a flexible schema that can be extended
    extra_config: Dict[str, Any] = {}

    def __init__(self, **data: Any):
        # Set default values for nested objects if not provided
        if 'api' not in data:
            data['api'] = {}
        if 'external_apis' not in data:
            data['external_apis'] = {}
        if 'system' not in data:
            data['system'] = {}
        super().__init__(**data)