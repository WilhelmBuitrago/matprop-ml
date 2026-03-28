"""Versioned immutable prompt templates for crystal generation."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .schema import GenerationMode


@dataclass(frozen=True)
class CrystalGenPromptConfig:
    version: str
    SYSTEM_MESSAGES: Mapping[str, str]
    INPUT_TEMPLATES: Mapping[str, str]
    CONDITIONAL_TEMPLATES: Mapping[str, str]
    OUTPUT_FORMAT_BLOCK: str
    CONSTRAINTS_BLOCK: str


def _freeze(data: dict[str, str]) -> Mapping[str, str]:
    return MappingProxyType(dict(data))


CRYSTAL_PROMPT_CONFIG_V1 = CrystalGenPromptConfig(
    version="v1",
    SYSTEM_MESSAGES=_freeze(
        {
            GenerationMode.CONDITIONAL.value: (
                "You are a crystallography assistant. Produce physically plausible crystal "
                "structures consistent with the provided composition and symmetry constraints."
            ),
            GenerationMode.INFILL.value: (
                "You complete partially known crystal structures while preserving existing "
                "lattice and symmetry information."
            ),
            GenerationMode.FORMULA_COMPUTE.value: (
                "You derive a plausible crystal structure from a target formula."
            ),
            GenerationMode.ELEMENT_GENERATION.value: (
                "You design a plausible crystal structure constrained only by the listed elements."
            ),
            GenerationMode.UNCONDITIONAL.value: (
                "You generate a conservative physically plausible crystal structure."
            ),
        }
    ),
    INPUT_TEMPLATES=_freeze(
        {
            GenerationMode.CONDITIONAL.value: "Generate a crystal structure satisfying the provided material description.",
            GenerationMode.INFILL.value: "Fill missing structural information for the specified crystal.",
            GenerationMode.FORMULA_COMPUTE.value: "Generate a plausible crystal structure from the formula.",
            GenerationMode.ELEMENT_GENERATION.value: "Generate a plausible structure using only the provided element set.",
            GenerationMode.UNCONDITIONAL.value: "Generate one physically plausible crystal structure.",
        }
    ),
    CONDITIONAL_TEMPLATES=_freeze(
        {
            "composition": "Composition:\n- Formula: {formula}\n- Elements: {elements}",
            "composition_spacegroup": "Composition + Symmetry:\n- Formula: {formula}\n- Space group: {space_group}",
            "lattice_atoms": "Lattice preference:\n- Lattice type: {lattice_type}",
            "elements": "Elements:\n- {elements}",
        }
    ),
    OUTPUT_FORMAT_BLOCK=(
        "Return ONLY CIF text. Start with a data_ header and include valid cell parameters and atomic positions. "
        "Do not include markdown, explanations, or prefixes."
    ),
    CONSTRAINTS_BLOCK=(
        "Physical plausibility constraints:\n"
        "- Non-degenerate lattice (positive volume).\n"
        "- Realistic interatomic distances (no atom overlap).\n"
        "- Fractional coordinates must be between 0 and 1."
    ),
)
