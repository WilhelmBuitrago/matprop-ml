"""Validation layer for parsed crystal structures."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymatgen.core.periodic_table import Element

from .constants import DEFAULT_MIN_DISTANCE_ANGSTROM, MIN_DISTANCE_THRESHOLDS
from .post_processor import ParsedStructure


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class PyMatgenValidator:
    """Runs structural plausibility checks using pymatgen primitives."""

    def validate(self, parsed: ParsedStructure) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        structure = parsed.structure

        if structure.lattice.volume <= 0:
            errors.append("invalid_lattice_volume")

        if len(structure) == 0:
            errors.append("empty_structure")

        for site in structure:
            element = str(site.specie)
            if not Element.is_valid_symbol(element):
                errors.append(f"invalid_species:{element}")
            for coord in site.frac_coords:
                if coord < 0.0 or coord > 1.0:
                    errors.append("fractional_coordinates_out_of_range")
                    break

        for i in range(len(structure)):
            for j in range(i + 1, len(structure)):
                e1 = str(structure[i].specie)
                e2 = str(structure[j].specie)
                pair = tuple(sorted((e1, e2)))
                threshold = MIN_DISTANCE_THRESHOLDS.get(
                    pair,
                    DEFAULT_MIN_DISTANCE_ANGSTROM,
                )
                distance = float(structure.get_distance(i, j))
                if distance < threshold:
                    warnings.append(
                        f"short_distance:{e1}-{e2}:{distance:.3f}< {threshold:.3f}"
                    )
                    if distance < max(0.8, threshold * 0.6):
                        errors.append(
                            f"severe_overlap:{e1}-{e2}:{distance:.3f}< {threshold:.3f}"
                        )

        is_valid = len(errors) == 0
        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)
