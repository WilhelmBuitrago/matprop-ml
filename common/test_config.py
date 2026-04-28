"""
Test script for the centralized configuration loader.
"""
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_config_loader():
    """Test the configuration loader functionality"""
    from common.config import config
    
    print("Testing configuration loader...")
    
    # Test loading configuration
    loaded_config = config.get_config()
    print(f"Loaded configuration: {type(loaded_config)}")
    
    # Test accessing specific sections
    print(f"API config: {loaded_config.api}")
    print(f"System config: {loaded_config.system}")
    
    # Test accessing models
    print(f"Models: {list(loaded_config.models.keys())}")
    for model_name, model_config in loaded_config.models.items():
        print(f"  {model_name}: {model_config.provider}/{model_config.model_name}")
    
    # Test the get method
    print(f"Planner model: {config.get('models.planner.model_name', 'default')}")
    print(f"Non-existent path: {config.get('models.nonexistent', 'default_value')}")
    
    # Test reload functionality
    print("Reloading configuration...")
    reload_success = config.reload()
    print(f"Reload successful: {reload_success}")

if __name__ == "__main__":
    test_config_loader()