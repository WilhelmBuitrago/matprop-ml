"""Centralized model registry resolved from the centralized configuration system."""

from __future__ import annotations

from typing import Dict, Optional, List, Union
import logging

# Use the new REST-based client
try:
    from common.config_client import client as config
except ImportError:
    # Fallback for import issues during transition
    from common.config import config

logger = logging.getLogger(__name__)

class ModelConfig:
    """Configuration for a specific model."""
    
    def __init__(self, provider: str, model_name: str, temperature: float = 0.7, max_tokens: int = 1000,
                 top_p: float = 1.0, frequency_penalty: float = 0.0, presence_penalty: float = 0.0):
        self.provider = provider
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
    
    def to_provider_model_string(self) -> str:
        """Convert to provider:model string format."""
        return f"{self.provider}:{self.model_name}"

def _get_model_config(model_key: str, default_provider: str = "ollama", 
                      default_model: str = "deepseek-r1:8b") -> ModelConfig:
    """
    Get model configuration from centralized config.
    
    Args:
        model_key: Key to look up in the config (e.g., "planner", "evaluator")
        default_provider: Default provider if not found in config
        default_model: Default model name if not found in config
        
    Returns:
        ModelConfig with provider and model information
    """
    # Try to get the model configuration from centralized config
    provider = config.get(f"models.{model_key}.provider")
    model_name = config.get(f"models.{model_key}.model_name")
    
    if provider is None or model_name is None:
        # Try to get default model configuration
        default_provider_config = config.get(f"models.default.provider")
        default_model_config = config.get(f"models.default.model_name")
        
        if default_provider_config:
            default_provider = default_provider_config
            
        if default_model_config:
            default_model = default_model_config
            
        # If still no config, log critical warning and use safe defaults
        if provider is None and model_key != "default":
            logger.critical(f"Model '{model_key}' not found in config. Using default provider: {default_provider}")
            provider = default_provider
            
        if model_name is None and model_key != "default":
            logger.critical(f"Model name for '{model_key}' not found in config. Using default model: {default_model}")
            model_name = default_model
            
        # If this is the default model itself and it's missing, use hardcoded safe defaults
        if model_key == "default":
            provider = provider or default_provider
            model_name = model_name or default_model
    
    # Get additional model parameters from centralized config
    temperature = config.get(f"models.{model_key}.temperature", 0.7)
    max_tokens = config.get(f"models.{model_key}.max_tokens", 1000)
    top_p = config.get(f"models.{model_key}.top_p", 1.0)
    frequency_penalty = config.get(f"models.{model_key}.frequency_penalty", 0.0)
    presence_penalty = config.get(f"models.{model_key}.presence_penalty", 0.0)
    
    return ModelConfig(provider or default_provider, model_name or default_model, 
                       temperature, max_tokens, top_p, frequency_penalty, presence_penalty)


def get_fallback_chain(role: str) -> List[str]:
    """
    Get the fallback chain for a specific role from centralized configuration.
    
    Args:
        role: The agent role (e.g., 'evaluator', 'planner', 'final')
        
    Returns:
        List of provider:model strings in order of preference
    """
    fallback_chain = []
    
    # Check for role-specific fallback chain in config
    fallback_value = config.get(f"models.{role}.fallback_chain")
    if fallback_value:
        if isinstance(fallback_value, str):
            fallback_chain = [model.strip() for model in fallback_value.split(",")]
        elif isinstance(fallback_value, list):
            fallback_chain = fallback_value
    
    # If no fallback chain specified, use default chain from config
    if not fallback_chain:
        default_chain = config.get("models.default_fallback_chain", ["ollama", "openrouter"])
        fallback_chain = default_chain if isinstance(default_chain, list) else ["ollama", "openrouter"]
    
    return fallback_chain


# Load model configurations from centralized config
_embedding_model_config = _get_model_config("embedding", "ollama", "mxbai-embed-large")
EMBEDDING_MODEL = _embedding_model_config.to_provider_model_string()

_base_model_config = _get_model_config("base", "ollama", "deepseek-r1:8b")
AGENT_BASE_MODEL = _base_model_config.to_provider_model_string()

_planning_evaluator_config = _get_model_config("planning_evaluator", "ollama", AGENT_BASE_MODEL)
PLANNING_EVALUATOR_MODEL = _planning_evaluator_config.to_provider_model_string()

# Backward-compatible aliases for existing consumers.
_evaluator_model_config = _get_model_config("evaluator", "ollama", PLANNING_EVALUATOR_MODEL)
EVALUATOR_MODEL = _evaluator_model_config.to_provider_model_string()

_planner_model_config = _get_model_config("planner", "ollama", PLANNING_EVALUATOR_MODEL)
PLANNER_MODEL = _planner_model_config.to_provider_model_string()

_insights_model_config = _get_model_config("insights", "ollama", AGENT_BASE_MODEL)
INSIGHTS_MODEL = _insights_model_config.to_provider_model_string()

_final_model_config = _get_model_config("final", "ollama", AGENT_BASE_MODEL)
FINAL_MODEL = _final_model_config.to_provider_model_string()

_cif_model_config = _get_model_config("cif", "ollama", "WilhelmBuitrago/llamat-3-cif-8b:Q5_K_M")
CIF_MODEL = _cif_model_config.to_provider_model_string()

_domain_critic_model_config = _get_model_config("domain_critic", "ollama", "WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M")
DOMAIN_CRITIC_MODEL = _domain_critic_model_config.to_provider_model_string()

# Agent components with specific provider:model configurations
PLANNER_CONFIG = config.get("models.planner.config", "ollama:deepseek-r1:8b")
EVALUATOR_CONFIG = config.get("models.evaluator.config", "ollama:deepseek-r1:8b")
DOMAIN_CRITIC_CONFIG = config.get("models.domain_critic.config", "openrouter:meta-llama/llama-3.1-70b-instruct:free")
INSIGHTS_CONFIG = config.get("models.insights.config", "ollama:deepseek-r1:8b")
FINAL_CONFIG = config.get("models.final.config", "openrouter:meta-llama/llama-3.1-70b-instruct:free")

# Backward-compatible dictionary for existing consumers.
GENERATION_MODELS = {
    "evaluator": EVALUATOR_MODEL,
    "final": FINAL_MODEL,
    "cif": CIF_MODEL,
}

# Create ModelConfig objects for all models to access parameters
ALL_MODEL_CONFIGS = {
    "embedding": _embedding_model_config,
    "evaluator": _evaluator_model_config,
    "planning_evaluator": _planning_evaluator_config,
    "planner": _planner_model_config,
    "insights": _insights_model_config,
    "final": _final_model_config,
    "cif": _cif_model_config,
    "domain_critic": _domain_critic_model_config,
}

# Pulled automatically at startup.
ALL_MODELS = sorted(
    {
        EMBEDDING_MODEL,
        EVALUATOR_MODEL,
        PLANNING_EVALUATOR_MODEL,
        INSIGHTS_MODEL,
        PLANNER_MODEL,
        FINAL_MODEL,
        CIF_MODEL,
        DOMAIN_CRITIC_MODEL,
    }
)
