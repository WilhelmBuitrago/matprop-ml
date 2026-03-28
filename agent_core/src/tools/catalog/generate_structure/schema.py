"""Strong schema contracts for crystal generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GenerationMode(str, Enum):
    CONDITIONAL = "conditional"
    INFILL = "infill"
    FORMULA_COMPUTE = "formula_compute"
    ELEMENT_GENERATION = "element_generation"
    UNCONDITIONAL = "unconditional"


@dataclass(frozen=True)
class CrystalSpec:
    """Canonical generation contract shared across pipeline stages."""

    formula: str | None = None
    lattice_type: str | None = None
    space_group: str | None = None
    elements: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    generation_mode: GenerationMode = GenerationMode.UNCONDITIONAL

    @property
    def has_lattice(self) -> bool:
        return bool(self.lattice_type)

    @property
    def has_symmetry(self) -> bool:
        return bool(self.space_group)

    @staticmethod
    def infer_mode(
        formula: str | None,
        elements: list[str],
        constraints: dict[str, Any],
        preferred: str | None = None,
    ) -> GenerationMode:
        if preferred:
            for mode in GenerationMode:
                if mode.value == preferred:
                    return mode

        if bool(constraints.get("infill")):
            return GenerationMode.INFILL
        if formula and (constraints.get("compute_only") is True):
            return GenerationMode.FORMULA_COMPUTE
        if formula:
            return GenerationMode.CONDITIONAL
        if elements:
            return GenerationMode.ELEMENT_GENERATION
        return GenerationMode.UNCONDITIONAL

    @classmethod
    def build(
        cls,
        *,
        formula: str | None,
        lattice_type: str | None,
        space_group: str | None,
        elements: list[str],
        constraints: dict[str, Any] | None = None,
        preferred_mode: str | None = None,
    ) -> "CrystalSpec":
        clean_elements = sorted({el for el in elements if el})
        safe_constraints = constraints or {}
        mode = cls.infer_mode(
            formula=formula,
            elements=clean_elements,
            constraints=safe_constraints,
            preferred=preferred_mode,
        )
        return cls(
            formula=formula,
            lattice_type=lattice_type,
            space_group=space_group,
            elements=clean_elements,
            constraints=safe_constraints,
            generation_mode=mode,
        )
