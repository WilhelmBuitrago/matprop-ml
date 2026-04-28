from fastapi import FastAPI, HTTPException, status, Request, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse
from fastapi import Header
import os
import json
from typing import Dict, Any, Optional
from pydantic import ValidationError
from pydantic import BaseModel
import sys
import os
from datetime import datetime

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import using absolute paths
from config_schema import ConfigSchema, ModelConfig, APIConfig, SystemConfig, ModelProvider
from config_persistence import ConfigPersistence
from audit_log import AuditLogger

# Global configuration instance
current_config: ConfigSchema = None
config_persistence: ConfigPersistence = None
audit_logger: AuditLogger = None

app = FastAPI(
    title="Centralized Configuration Service",
    description="A service for managing centralized configuration for the entire system",
    version="1.0.0"
)

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed response"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error.get("loc", [])),
            "message": error.get("msg", "Validation error"),
            "type": error.get("type", "validation_error")
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "code": "VALIDATION_ERROR",
            "details": errors
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "code": exc.status_code,
            "details": exc.detail
        }
    )

def calculate_config_diff(old_config: ConfigSchema, new_config: ConfigSchema) -> Dict[str, Any]:
    """Calculate the differences between two configuration objects"""
    old_dict = old_config.dict() if old_config else {}
    new_dict = new_config.dict()
    
    changes = {}
    
    def compare_dicts(old, new, path=""):
        diff = {}
        for key in set(old.keys()) | set(new.keys()):
            old_val = old.get(key, None)
            new_val = new.get(key, None)
            
            if old_val != new_val:
                if isinstance(old_val, dict) and isinstance(new_val, dict):
                    nested_diff = compare_dicts(old_val, new_val, f"{path}.{key}" if path else key)
                    if nested_diff:
                        diff.update(nested_diff)
                elif isinstance(old_val, dict) or isinstance(new_val, dict):
                    diff[f"{path}.{key}" if path else key] = {
                        "old": old_val,
                        "new": new_val
                    }
                else:
                    diff[f"{path}.{key}" if path else key] = {
                        "old": old_val,
                        "new": new_val
                    }
        return diff
    
    return compare_dicts(old_dict, new_dict)


def validate_api_key(x_api_key: Optional[str] = Header(None)):
    """Validate API key for protected endpoints"""
    # In a real implementation, this would check against a secure key store
    # For now, we'll use a simple check for demonstration
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing"
        )
    
    # This is a placeholder - in a real system, you would validate the key against a secure store
    # For now, we'll accept any non-empty key as valid for demonstration purposes
    if not x_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is invalid"
        )

def validate_cross_field_constraints(config: ConfigSchema) -> list:
    """Validate cross-field constraints in the configuration"""
    errors = []
    
    # Validate model provider configurations
    for model_name, model_config in config.models.items():
        # Check if API key is required but missing
        if model_config.provider in [ModelProvider.OPENAI, ModelProvider.ANTHROPIC, ModelProvider.GROQ, ModelProvider.TOGETHER]:
            if not model_config.api_key:
                errors.append(f"Model '{model_name}' requires an API key for provider '{model_config.provider.value}'")
        elif model_config.provider == ModelProvider.OLLAMA:
            # Check if Ollama provider has host configured when used
            if not config.system.extra_config.get("OLLAMA_HOST"):
                errors.append(f"Model '{model_name}' uses Ollama provider but OLLAMA_HOST is not configured in system settings")
    
    # Validate external API configurations
    # Check that required API keys are provided when services are enabled
    if config.external_apis.mp_api_key is None:
        # Check if MP API is being used somewhere that requires it
        pass  # This would require checking actual usage
    
    # Validate GPU-related configurations if applicable
    gpu_configured = config.system.extra_config.get("GPU_ENABLED", False)
    if gpu_configured:
        # Check if GPU-related settings are consistent
        pass  # Add GPU validation logic here if needed
    
    # Additional cross-field validations can be added here
    
    return errors


def validate_external_api_credentials(config: ConfigSchema) -> list:
    """Validate external API credentials with lightweight API calls"""
    errors = []
    
    # Validate Materials Project API key if provided
    if config.external_apis.mp_api_key:
        try:
            # Attempt a lightweight validation call to Materials Project API
            import requests
            validation_url = "https://api.materialsproject.org/materials/summary/mp-149"
            headers = {
                "X-API-KEY": config.external_apis.mp_api_key
            }
            response = requests.get(validation_url, headers=headers, timeout=10)
            if response.status_code == 401:
                errors.append({
                    "type": "error",
                    "message": "Materials Project API key is invalid"
                })
            elif response.status_code != 200 and response.status_code != 404:
                errors.append({
                    "type": "error",
                    "message": f"Materials Project API validation failed with status {response.status_code}"
                })
        except Exception as e:
            errors.append({
                "type": "error",
                "message": f"Error validating Materials Project API key: {str(e)}"
            })
    
    # Validate Semantic Scholar API key if provided
    if config.external_apis.semantic_scholar_api_key:
        try:
            # Attempt a lightweight validation call to Semantic Scholar API
            import requests
            validation_url = "https://api.semanticscholar.org/test"
            response = requests.get(validation_url, timeout=10)
            # We don't check the response status here as we just want to test connectivity
        except Exception as e:
            errors.append({
                "type": "error",
                "message": f"Error validating Semantic Scholar API key: {str(e)}"
            })
    
    # Validate OpenRouter API key if provided
    if config.external_apis.openrouter_api_key:
        try:
            # Attempt a lightweight validation call to OpenRouter API
            import requests
            import json
            headers = {
                "Authorization": f"Bearer {config.external_apis.openrouter_api_key}",
                "Content-Type": "application/json"
            }
            validation_url = "https://openrouter.ai/api/v1/models"
            response = requests.get(validation_url, headers=headers, timeout=10)
            if response.status_code == 401:
                errors.append({
                    "type": "error",
                    "message": "OpenRouter API key is invalid"
                })
            elif response.status_code != 200:
                errors.append({
                    "type": "error",
                    "message": f"OpenRouter API validation failed with status {response.status_code}"
                })
        except Exception as e:
            errors.append({
                "type": "error",
                "message": f"Error validating OpenRouter API key: {str(e)}"
            })
    
    return errors


def validate_hardware_acceleration(config: ConfigSchema) -> list:
    """Validate hardware acceleration availability"""
    errors = []
    
    # Check for GPU availability if enabled
    gpu_enabled = config.system.extra_config.get("GPU_ENABLED", False)
    if gpu_enabled:
        try:
            import torch
            # Check if CUDA is available when GPU is enabled
            if not torch.cuda.is_available():
                errors.append("GPU is enabled but CUDA is not available")
        except ImportError:
            errors.append("GPU is enabled but PyTorch is not available")
        except Exception as e:
            errors.append(f"Error checking GPU availability: {str(e)}")
    
    return errors


def validate_range_constraints(config: ConfigSchema) -> list:
    """Validate numeric parameter ranges"""
    errors = []
    
    # Validate API configuration ranges
    if config.api.port < 1 or config.api.port > 65535:
        errors.append({
            "type": "error",
            "message": f"API port {config.api.port} is outside valid range (1-65535)"
        })
    
    # Validate system configuration ranges
    if config.system.timeout < 1:
        errors.append({
            "type": "error",
            "message": f"System timeout {config.system.timeout} must be positive"
        })
    elif config.system.timeout > 300:
        errors.append({
            "type": "error", 
            "message": f"System timeout {config.system.timeout} exceeds maximum (300)"
        })
    
    # Validate model configuration ranges
    for model_name, model_config in config.models.items():
        # Temperature validation (now 0.0-2.0)
        if model_config.temperature < 0.0 or model_config.temperature > 2.0:
            errors.append({
                "type": "warning",
                "message": f"Model '{model_name}' temperature {model_config.temperature} is outside valid range (0.0-2.0)"
            })
        
        # Max tokens validation
        if model_config.max_tokens < 1 or model_config.max_tokens > 4096:
            errors.append({
                "type": "warning",
                "message": f"Model '{model_name}' max_tokens {model_config.max_tokens} is outside valid range (1-4096)"
            })
        
        # Top-p validation
        if model_config.top_p < 0.0 or model_config.top_p > 1.0:
            errors.append({
                "type": "warning",
                "message": f"Model '{model_name}' top_p {model_config.top_p} is outside valid range (0.0-1.0)"
            })
        
        # Frequency penalty validation
        if model_config.frequency_penalty < -2.0 or model_config.frequency_penalty > 2.0:
            errors.append({
                "type": "warning",
                "message": f"Model '{model_name}' frequency_penalty {model_config.frequency_penalty} is outside valid range (-2.0 to 2.0)"
            })
        
        # Presence penalty validation
        if model_config.presence_penalty < -2.0 or model_config.presence_penalty > 2.0:
            errors.append({
                "type": "warning",
                "message": f"Model '{model_name}' presence_penalty {model_config.presence_penalty} is outside valid range (-2.0 to 2.0)"
            })
    
    return errors


def validate_provider_model_compatibility(config: ConfigSchema) -> list:
    """Validate that models are compatible with their providers"""
    errors = []
    
    # Define supported models for each provider
    PROVIDER_MODEL_MAP = {
        ModelProvider.OPENAI: {
            'gpt-4', 'gpt-4-turbo', 'gpt-4o', 'gpt-3.5-turbo', 'gpt-4-1106-preview'
        },
        ModelProvider.ANTHROPIC: {
            'claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku', 'claude-2.1', 'claude-2.0'
        },
        ModelProvider.GROQ: {
            'llama3-70b-8192', 'llama3-8b-8192', 'mixtral-8x7b-32768', 'gemma-7b-it'
        },
        ModelProvider.OLLAMA: {
            'llama3', 'llama2', 'mistral', 'neural-chat', 'starling-lm', 'openhermes',
            'dolphin-mistral', 'nomic-embed-text'
        },
        ModelProvider.TOGETHER: {
            'mistral-7b-instruct', 'mixtral-8x7b-instruct', 'llama-2-70b-chat', 
            'llama-2-13b-chat', 'llama-3-70b', 'llama-3-8b'
        }
    }
    
    # Define provider-specific parameter constraints
    PROVIDER_PARAMETER_CONSTRAINTS = {
        ModelProvider.OPENAI: {
            'temperature_range': (0.0, 2.0),
            'max_tokens_range': (1, 4096),
            'supports_top_p': True,
            'supports_frequency_penalty': True,
            'supports_presence_penalty': True
        },
        ModelProvider.ANTHROPIC: {
            'temperature_range': (0.0, 1.0),
            'max_tokens_range': (1, 4096),
            'supports_top_p': True,
            'supports_frequency_penalty': False,
            'supports_presence_penalty': False
        },
        ModelProvider.GROQ: {
            'temperature_range': (0.0, 2.0),
            'max_tokens_range': (1, 8192),
            'supports_top_p': True,
            'supports_frequency_penalty': False,
            'supports_presence_penalty': False
        },
        ModelProvider.OLLAMA: {
            'temperature_range': (0.0, 2.0),
            'max_tokens_range': (1, 4096),
            'supports_top_p': True,
            'supports_frequency_penalty': True,
            'supports_presence_penalty': True
        },
        ModelProvider.TOGETHER: {
            'temperature_range': (0.0, 1.0),
            'max_tokens_range': (1, 8192),
            'supports_top_p': True,
            'supports_frequency_penalty': True,
            'supports_presence_penalty': True
        }
    }
    
    # Validate each model against its provider
    for model_name, model_config in config.models.items():
        provider = model_config.provider
        model = model_config.model_name
        
        # Check if provider supports this model
        if provider in PROVIDER_MODEL_MAP:
            supported_models = PROVIDER_MODEL_MAP.get(provider, set())
            if model not in supported_models and len(supported_models) > 0:
                # Check if it's a known model for this provider
                valid_model = False
                for supported_model in supported_models:
                    if model.startswith(supported_model) or model == supported_model:
                        valid_model = True
                        break
                
                if not valid_model:
                    errors.append({
                        "type": "error",
                        "message": f"Model '{model}' is not supported by provider '{provider.value}' for model '{model_name}'"
                    })
        
        # Check provider-specific parameter constraints
        if provider in PROVIDER_PARAMETER_CONSTRAINTS:
            constraints = PROVIDER_PARAMETER_CONSTRAINTS[provider]
            
            # Validate temperature range for provider
            temp_min, temp_max = constraints['temperature_range']
            if model_config.temperature < temp_min or model_config.temperature > temp_max:
                errors.append({
                    "type": "warning",
                    "message": f"Model '{model_name}' temperature {model_config.temperature} is outside provider-specific range ({temp_min}-{temp_max})"
                })
            
            # Validate max_tokens range for provider
            tokens_min, tokens_max = constraints['max_tokens_range']
            if model_config.max_tokens < tokens_min or model_config.max_tokens > tokens_max:
                errors.append({
                    "type": "warning",
                    "message": f"Model '{model_name}' max_tokens {model_config.max_tokens} is outside provider-specific range ({tokens_min}-{tokens_max})"
                })
            
            # Validate parameter support for provider
            if not constraints['supports_top_p'] and model_config.top_p != 1.0:
                errors.append({
                    "type": "warning",
                    "message": f"Model '{model_name}' uses top_p parameter that may not be supported by provider '{provider.value}'"
                })
            
            if not constraints['supports_frequency_penalty'] and model_config.frequency_penalty != 0.0:
                errors.append({
                    "type": "warning",
                    "message": f"Model '{model_name}' uses frequency_penalty parameter that may not be supported by provider '{provider.value}'"
                })
            
            if not constraints['supports_presence_penalty'] and model_config.presence_penalty != 0.0:
                errors.append({
                    "type": "warning",
                    "message": f"Model '{model_name}' uses presence_penalty parameter that may not be supported by provider '{provider.value}'"
                })
    
    return errors


def validate_fallback_chain(config: ConfigSchema) -> list:
    """Validate that fallback chain models are correctly configured"""
    errors = []
    
    # Check if fallback chain is defined in system config
    fallback_chain = config.system.extra_config.get("fallback_models", [])
    
    if isinstance(fallback_chain, list) and len(fallback_chain) > 0:
        # Validate each model in the fallback chain
        for i, model_ref in enumerate(fallback_chain):
            if not isinstance(model_ref, str):
                errors.append({
                    "type": "error", 
                    "message": f"Invalid fallback chain entry at position {i}: must be a string reference to a model"
                })
                continue
                
            # Check if model exists in configuration
            if model_ref not in config.models:
                errors.append({
                    "type": "error",
                    "message": f"Model '{model_ref}' in fallback chain is not defined in models configuration"
                })
                continue
                
            # Validate the model configuration
            model_config = config.models[model_ref]
            validation_result = validate_model_configuration(model_ref, model_config)
            if not validation_result["valid"]:
                for error in validation_result["errors"]:
                    errors.append({
                        "type": "error",
                        "message": f"Model '{model_ref}' in fallback chain is invalid: {error['message']}"
                    })
    
    return errors


def validate_model_configuration(model_name: str, model_config: ModelConfig) -> dict:
    """Validate individual model configuration for consistency"""
    errors = []
    validation_result = {"valid": True, "errors": []}
    
    # Validate provider-model compatibility
    if not is_model_compatible_with_provider(model_config.model_name, model_config.provider):
        errors.append({
            "type": "error",
            "message": f"Model '{model_config.model_name}' is not compatible with provider '{model_config.provider.value}'"
        })
        validation_result["valid"] = False
        validation_result["errors"] = errors
        return validation_result
    
    # Validate that model is explicitly defined (no implicit models)
    # This is ensured by the fact that we're validating against the config.models entries
    
    validation_result["errors"] = errors
    return validation_result


def is_model_compatible_with_provider(model_name: str, provider: ModelProvider) -> bool:
    """Check if a model is compatible with its provider"""
    # Define known model-provider compatibility
    PROVIDER_MODEL_COMPATIBILITY = {
        ModelProvider.OPENAI: ['gpt-', 'text-', 'code-'],
        ModelProvider.ANTHROPIC: ['claude-'],
        ModelProvider.GROQ: ['llama2', 'llama3', 'mixtral', 'gemma'],
        ModelProvider.OLLAMA: ['llama', 'mistral', 'neural-chat', 'starling', 'openhermes', 'dolphin'],
        ModelProvider.TOGETHER: ['llama', 'mistral', 'together']
    }
    
    if provider in PROVIDER_MODEL_COMPATIBILITY:
        compatible_prefixes = PROVIDER_MODEL_COMPATIBILITY[provider]
        for prefix in compatible_prefixes:
            if model_name.startswith(prefix):
                return True
        return False
    return True  # Allow unknown providers to pass through

def validate_config(config: ConfigSchema):
    """Validate configuration without applying or applying or persisting it"""
    try:
        # Validate against Pydantic schema
        validated_config = ConfigSchema(**config.dict())
        
        # Perform all validation checks
        validation_errors = []
        
        # 1. Basic Pydantic validation (already done by creating ConfigSchema instance)
        # 2. Cross-field validation
        cross_field_errors = validate_cross_field_constraints(validated_config)
        validation_errors.extend(cross_field_errors)
        
        # 3. External API credential validation
        external_api_errors = validate_external_api_credentials(validated_config)
        validation_errors.extend(external_api_errors)
        
        # 4. Hardware acceleration validation
        hardware_errors = validate_hardware_acceleration(validated_config)
        validation_errors.extend(hardware_errors)
        
        # 5. Range validation
        range_errors = validate_range_constraints(validated_config)
        validation_errors.extend(range_errors)
        
        # 6. Provider-model compatibility validation
        provider_model_errors = validate_provider_model_compatibility(validated_config)
        validation_errors.extend(provider_model_errors)
        
        # 7. Fallback chain validation
        fallback_errors = validate_fallback_chain(validated_config)
        validation_errors.extend(fallback_errors)
        
        # 8. Individual model configuration validation
        for model_name, model_config in validated_config.models.items():
            model_validation = validate_model_configuration(model_name, model_config)
            if not model_validation["valid"]:
                validation_errors.extend(model_validation["errors"])
        
        if validation_errors:
            return {
                "valid": False,
                "errors": validation_errors
            }
        
        return {
            "valid": True,
            "errors": []
        }
    except ValidationError as e:
        # Extract detailed error information
        errors = []
        for error in e.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error.get("loc", ["unknown"])),
                "message": error.get("msg", "Validation error"),
                "type": error.get("type", "validation_error")
            })
        return {
            "valid": False,
            "errors": errors
        }
    except Exception as e:
        return {
            "valid": False,
            "errors": [{"type": "error", "message": str(e)}]
        }

@app.on_event("startup")
async def startup_event():
    """Initialize the configuration service on startup"""
    global current_config, config_persistence, audit_logger
    config_persistence = ConfigPersistence()
    audit_logger = AuditLogger()
    
    # Load existing configuration or create default
    try:
        current_config = config_persistence.load_config()
        if current_config is None:
            current_config = ConfigSchema()
    except Exception as e:
        print(f"Error loading config: {e}")
        current_config = ConfigSchema()
    
    print("Configuration service started")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "config_service"}

@app.get("/config")
async def get_config():
    """Get the current configuration - Fast read endpoint"""
    global current_config
    return current_config

@app.put("/config")
async def update_config(config: ConfigSchema, x_api_key: str = Header(None)):
    """Update the configuration - Mandatory validation before writing"""
    global current_config, audit_logger
    try:
        # Validate the configuration first (re-validate before writing to prevent race conditions)
        validation_result = validate_config(config)
        if not validation_result["valid"]:
            # Return validation errors with proper format
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "status": "error",
                    "code": "VALIDATION_FAILED",
                    "details": validation_result["errors"]
                }
            )
        
        # Validate API key for write operations
        validate_api_key(x_api_key)
        
        # Calculate changes for audit log
        changes = calculate_config_diff(current_config, config)
        
        # Save the configuration
        old_config = current_config
        current_config = config
        # Only save if config_persistence is initialized
        if config_persistence is not None:
            config_persistence.save_config(current_config)
            
            # Log the change if audit_logger is available
            if audit_logger is not None:
                try:
                    audit_logger.log_change(
                        user="admin",  # In a real implementation, this would come from authentication
                        changes=changes,
                        validation_result=validation_result
                    )
                except Exception as e:
                    print(f"Failed to log audit entry: {e}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "message": "Configuration updated successfully"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "status": "error",
            "code": "INTERNAL_ERROR",
            "details": f"Failed to update configuration: {str(e)}"
        })

@app.post("/config/validate")
async def validate_config_endpoint(config: ConfigSchema):
    """Validate configuration without applying or persisting it - Stateless, no side effects"""
    validation_result = validate_config(config)
    if not validation_result["valid"]:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=validation_result
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=validation_result
    )


@app.get("/config/history")
async def get_config_history(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    config_key: Optional[str] = None
):
    """Get the configuration change history"""
    global audit_logger
    if audit_logger is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Audit logging not available"
        )
    
    try:
        history = audit_logger.get_history(
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date,
            config_key=config_key
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "data": history,
                "total": audit_logger.get_entry_count() if audit_logger else 0
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {str(e)}"
        )