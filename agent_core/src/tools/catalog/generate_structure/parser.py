"""Hybrid parser phase 1: deterministic extraction from user query."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .constants import LATTICE_KEYWORDS

_FORMULA_RE = re.compile(r"\b([A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)+)\b")
_ELEMENT_RE = re.compile(r"[A-Z][a-z]?")
_SPACE_GROUP_RE = re.compile(r"\b([A-Z][A-Za-z0-9_\-/]{1,15})\b")


@dataclass(frozen=True)
class PartialCrystalSpec:
    formula: str | None = None
    lattice_type: str | None = None
    space_group: str | None = None
    elements: list[str] = field(default_factory=list)
    constraints: dict[str, object] = field(default_factory=dict)


class DeterministicCrystalParser:
    """Deterministic extraction of key crystal fields from natural language."""

    def parse(self, query: str) -> PartialCrystalSpec:
        text = (query or "").strip()
        formula = self.extract_formula(text)
        lattice_type = self.extract_lattice_type(text)
        space_group = self.extract_space_group(text)
        elements = self.extract_elements(text, formula)
        constraints = self.extract_constraints(text)
        return PartialCrystalSpec(
            formula=formula,
            lattice_type=lattice_type,
            space_group=space_group,
            elements=elements,
            constraints=constraints,
        )

    def extract_formula(self, query: str) -> str | None:
        match = _FORMULA_RE.search(query)
        return match.group(1) if match else None

    def extract_elements(self, query: str, formula: str | None) -> list[str]:
        if formula:
            return sorted(set(_ELEMENT_RE.findall(formula)))

        explicit = re.search(r"elements?\s*[:=]\s*([A-Za-z,\s]+)", query, re.IGNORECASE)
        if explicit:
            candidate = _ELEMENT_RE.findall(explicit.group(1))
            if candidate:
                return sorted(set(candidate))

        return []

    def extract_lattice_type(self, query: str) -> str | None:
        lowered = query.lower()
        for keyword, canonical in LATTICE_KEYWORDS.items():
            if keyword in lowered:
                return canonical
        return None

    def extract_space_group(self, query: str) -> str | None:
        for candidate in _SPACE_GROUP_RE.findall(query):
            if any(ch.isdigit() for ch in candidate) and any(
                ch.isalpha() for ch in candidate
            ):
                if (
                    any(symbol in candidate for symbol in ("-", "/", "_"))
                    or candidate[0].isupper()
                ):
                    return candidate
        return None

    def extract_constraints(self, query: str) -> dict[str, object]:
        lowered = query.lower()
        constraints: dict[str, object] = {}
        if "infill" in lowered:
            constraints["infill"] = True
        if "compute formula" in lowered:
            constraints["compute_only"] = True
        return constraints


def missing_critical_fields(spec: PartialCrystalSpec) -> bool:
    """Return True when LLM completion is required for critical fields."""
    if spec.formula:
        return False
    if spec.elements:
        return False
    return True
