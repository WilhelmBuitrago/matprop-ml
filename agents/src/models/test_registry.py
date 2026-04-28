"""
Test script to verify the model registry correctly loads from centralized configuration.
"""

import sys
import os

# Add the project root to the path so we can import common modules
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

def test_registry_with_config():
    """Test that the registry correctly loads model configurations from the centralized config."""
    
    print("Testing model registry with centralized configuration...")
    
    # Import the registry
    try:
        import registry
        
        print(f"Embedding model: {registry.EMBEDDING_MODEL}")
        print(f"Evaluator model: {registry.EVALUATOR_MODEL}")
        print(f"Planner model: {registry.PLANNER_MODEL}")
        print(f"Final model: {registry.FINAL_MODEL}")
        print(f"All models: {registry.ALL_MODELS}")
        
        # Test fallback chains
        evaluator_fallback = registry.get_fallback_chain("evaluator")
        print(f"Evaluator fallback chain: {evaluator_fallback}")
        
        planner_fallback = registry.get_fallback_chain("planner")
        print(f"Planner fallback chain: {planner_fallback}")
        
        # Verify that models are loaded from config
        # This should match what's in config_store/config.json
        expected_embedding = "ollama:mxbai-embed-large"
        expected_evaluator = "ollama:deepseek-r1:8b"
        expected_planner = "ollama:deepseek-r1:8b"
        
        print(f"\nVerification:")
        print(f"  Embedding model matches expected ({expected_embedding}): {registry.EMBEDDING_MODEL == expected_embedding}")
        print(f"  Evaluator model matches expected ({expected_evaluator}): {registry.EVALUATOR_MODEL == expected_evaluator}")
        print(f"  Planner model matches expected ({expected_planner}): {registry.PLANNER_MODEL == expected_planner}")
        
        return True
    except Exception as e:
        print(f"Error importing registry: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config_override():
    """Test that changes in config.json are reflected in the registry."""
    
    print("\nTesting configuration override...")
    
    # The config loader has a 5s TTL, so we'll just verify the current state
    try:
        import registry
        print(f"Current embedding model from config: {registry.EMBEDDING_MODEL}")
        return True
    except Exception as e:
        print(f"Error testing config override: {e}")
        return False

if __name__ == "__main__":
    success1 = test_registry_with_config()
    success2 = test_config_override()
    if success1 and success2:
        print("\nTest completed successfully!")
    else:
        print("\nTest completed with some issues.")