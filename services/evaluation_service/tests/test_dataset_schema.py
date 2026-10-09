from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from dataset_schema import validate_dataset_payload


def test_dataset_validation_accepts_extended_fields():
    payload = {
        "dataset_name": "smoke_set",
        "min_dataset_size_for_compare": 3,
        "min_cases_per_difficulty": 1,
        "cases": [
            {
                "query": "Find properties of mp-149",
                "expected_behavior": "Return material properties with concise summary",
                "expected_tools": ["search_materials", "get_material_properties"],
                "expected_outcome_type": "sufficient",
                "query_type": "simple",
                "difficulty": "easy",
                "weight": 1.0,
            },
            {
                "query": "Material lookup with missing id",
                "expected_behavior": "Handle missing material gracefully",
                "expected_tools": ["search_materials"],
                "expected_outcome_type": "failure",
                "query_type": "error-case",
                "difficulty": "medium",
                "weight": 1.2,
            },
            {
                "query": "Ambiguous query about bismuth structures",
                "expected_behavior": "Ask clarifying or provide partial answer",
                "expected_tools": ["search_materials"],
                "expected_outcome_type": "partial",
                "query_type": "ambigua",
                "difficulty": "hard",
                "weight": 1.5,
            },
        ],
    }
    result = validate_dataset_payload(payload)
    assert result["valid"] is True
    assert result["summary"]["cases_count"] == 3


def test_dataset_validation_rejects_invalid_weight():
    payload = {
        "dataset_name": "invalid_set",
        "cases": [
            {
                "query": "Find mp-149",
                "expected_behavior": "Return details",
                "expected_tools": ["search_materials"],
                "expected_outcome_type": "sufficient",
                "query_type": "simple",
                "difficulty": "easy",
                "weight": 0,
            }
        ],
    }
    result = validate_dataset_payload(payload)
    assert result["valid"] is False
