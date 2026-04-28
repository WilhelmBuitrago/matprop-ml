"""
Example of how to integrate the centralized configuration loader into existing services.

This example shows how to replace os.getenv() calls with the new configuration loader.
"""

# Before: Using os.getenv() directly
def old_way():
    import os
    provider = os.getenv("AGENT_PLANNER_PROVIDER", "ollama")
    model = os.getenv("AGENT_PLANNER_MODEL", "deepseek-r1:8b")
    return {"provider": provider, "model": model}

# After: Using the centralized configuration loader
def new_way():
    from common.config import config
    
    # Access configuration through the loader
    planner_config = config.get_config().models.get("planner")
    if planner_config:
        return {
            "provider": planner_config.provider,
            "model": planner_config.model_name
        }
    else:
        # Fallback to default values
        return {"provider": "ollama", "model": "deepseek-r1:8b"}

# Alternative way using the dot notation access
def new_way_alternative():
    from common.config import config
    
    # Access configuration sections directly
    models = config.models  # This accesses config.get_config().models
    api = config.api
    system = config.system
    
    # Get specific model configuration
    if "planner" in models:
        planner_model = models["planner"]
        return {
            "provider": planner_model.provider,
            "model": planner_model.model_name
        }
    
    return {"provider": "ollama", "model": "deepseek-r1:8b"}

# Even simpler access using the get method
def new_way_simple():
    from common.config import config
    
    # Simple path-based access
    provider = config.get("models.planner.provider", "ollama")
    model = config.get("models.planner.model_name", "deepseek-r1:8b")
    
    return {"provider": provider, "model": model}

if __name__ == "__main__":
    print("Old way:", old_way())
    print("New way:", new_way())
    print("New way alternative:", new_way_alternative())
    print("New way simple:", new_way_simple())