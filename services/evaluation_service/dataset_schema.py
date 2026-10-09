from __future__ import annotations

from enum import Enum
from hashlib import sha256
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


class QueryType(str, Enum):
    SIMPLE = "simple"
    MULTI_STEP = "multi-step"
    AMBIGUA = "ambigua"
    ERROR_CASE = "error-case"


class ExpectedOutcomeType(str, Enum):
    SUFFICIENT = "sufficient"
    FAILURE = "failure"
    PARTIAL = "partial"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class EvaluationCase(BaseModel):
    query: str = Field(min_length=3)
    expected_behavior: str = Field(min_length=3)
    expected_tools: List[str] = Field(default_factory=list)
    expected_outcome_type: ExpectedOutcomeType
    query_type: QueryType
    difficulty: Difficulty
    weight: float = Field(gt=0.0)

    @field_validator("query", "expected_behavior")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError("Text fields must not be empty")
        return normalized

    @field_validator("expected_tools")
    @classmethod
    def normalize_tools(cls, value: List[str]) -> List[str]:
        cleaned = []
        for tool_name in value:
            normalized = tool_name.strip()
            if normalized:
                cleaned.append(normalized)
        return cleaned

    def stable_id(self) -> str:
        digest = sha256(
            (
                f"{self.query}|{self.expected_behavior}|{self.query_type.value}|"
                f"{self.expected_outcome_type.value}|{self.difficulty.value}"
            ).encode("utf-8")
        ).hexdigest()
        return digest[:16]


class EvaluationDataset(BaseModel):
    dataset_name: str = Field(default="evaluation_dataset", min_length=3)
    min_dataset_size_for_compare: int = Field(default=10, ge=3)
    min_cases_per_difficulty: int = Field(default=1, ge=1)
    cases: List[EvaluationCase] = Field(min_length=1)

    @field_validator("dataset_name")
    @classmethod
    def normalize_dataset_name(cls, value: str) -> str:
        return "_".join(value.strip().split())

    @model_validator(mode="after")
    def validate_unique_cases(self) -> "EvaluationDataset":
        seen: set[str] = set()
        duplicates: List[str] = []
        for item in self.cases:
            case_id = item.stable_id()
            if case_id in seen:
                duplicates.append(case_id)
            seen.add(case_id)
        if duplicates:
            raise ValueError(f"Duplicate cases found: {duplicates}")
        return self

    def dataset_checksum(self) -> str:
        serialized = "\n".join(
            sorted(
                f"{case.stable_id()}|{case.weight:.6f}|{case.expected_outcome_type.value}"
                for case in self.cases
            )
        )
        return sha256(serialized.encode("utf-8")).hexdigest()


def validate_dataset_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []
    dataset: Optional[EvaluationDataset] = None

    try:
        dataset = EvaluationDataset.model_validate(payload)
    except ValidationError as exc:
        for issue in exc.errors():
            errors.append(
                {
                    "loc": ".".join(str(x) for x in issue.get("loc", [])),
                    "msg": issue.get("msg", "invalid field"),
                    "type": issue.get("type", "validation_error"),
                }
            )
    except ValueError as exc:
        errors.append({"loc": "dataset", "msg": str(exc), "type": "value_error"})

    if dataset is None:
        return {
            "valid": False,
            "errors": errors,
            "summary": {
                "cases_count": 0,
                "difficulty_distribution": {},
            },
        }

    difficulty_distribution: Dict[str, int] = {
        Difficulty.EASY.value: 0,
        Difficulty.MEDIUM.value: 0,
        Difficulty.HARD.value: 0,
    }

    for case in dataset.cases:
        difficulty_distribution[case.difficulty.value] += 1

    for difficulty, count in difficulty_distribution.items():
        if count < dataset.min_cases_per_difficulty:
            errors.append(
                {
                    "loc": "cases",
                    "msg": (
                        f"Insufficient cases for difficulty '{difficulty}': "
                        f"{count} < {dataset.min_cases_per_difficulty}"
                    ),
                    "type": "difficulty_coverage_error",
                }
            )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "summary": {
            "cases_count": len(dataset.cases),
            "difficulty_distribution": difficulty_distribution,
            "dataset_name": dataset.dataset_name,
            "dataset_checksum": dataset.dataset_checksum(),
        },
        "dataset": dataset.model_dump(mode="json"),
    }


def load_dataset(payload: Dict[str, Any]) -> Tuple[EvaluationDataset, Dict[str, Any]]:
    validation = validate_dataset_payload(payload)
    if not validation["valid"]:
        raise ValueError(
            {"message": "Invalid dataset", "details": validation["errors"]}
        )
    dataset = EvaluationDataset.model_validate(validation["dataset"])
    return dataset, validation
