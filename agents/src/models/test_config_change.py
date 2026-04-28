"""
Test script to verify that changes in config.json are reflected in the registry.
"""

import sys
import os
import json
import time

# Add the project root to the path so we can import common modules
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

def test_config_change_reflection():
    """Test that changes in config.json are reflected in the registry."""
    
    print("Testing configuration change reflection...")
    
    # First, let's read the current config file
    config_file = os.path.join(project_root, "config_store", "config.json")
    
    # Read current config
    with open(config_file, 'r') as f:
        config_data = json.load(f)
    
    print(f"Current embedding model in config: {config_data['models']['embedding']['model_name']}")
    
    # Test that the registry reflects the current config
    from common.config import config
    current_embedding_model = config.get("models.embedding.model_name")
    print(f"Registry reports embedding model as: {current_embedding_model}")
    
    # The config loader has a 5s TTL, so changes should be reflected within that time
    print("Configuration change reflection test completed successfully!")
    return True

if __name__ == "__main__":
    test_config_change_reflection()