"""Post-processing for model raw crystal outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:  # pragma: no cover - environment-dependent optional dependency
    from pymatgen.core import Structure
except Exception:  # pragma: no cover - handled at runtime
    Structure = None  # type: ignore[assignment]


@dataclass(frozen=True)
class AtomSite:
    element: str
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class ParsedStructure:
    lattice: dict[str, float]
    atoms: list[AtomSite]
    structure: Any
    errors: list[str] = field(default_factory=list)


class PostProcessor:
    """Normalize and parse raw model output into structured data."""

    def clean_raw_output(self, raw_output: str) -> str:
        cleaned = (raw_output or "").strip()
        cleaned = cleaned.replace("```cif", "").replace("```", "")
        for prefix in ("Assistant:", "assistant:", "Response:"):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix) :].strip()
        return cleaned

    def extract_cif_block(self, text: str) -> str:
        start = text.find("data_")
        if start < 0:
            raise ValueError("cif_header_not_found")
        return text[start:].strip()

    def parse(self, raw_output: str) -> ParsedStructure:
        if Structure is None:
            raise RuntimeError("pymatgen_not_installed")

        cleaned = self.clean_raw_output(raw_output)
        cif_text = self.extract_cif_block(cleaned)
        structure = Structure.from_str(cif_text, fmt="cif")

        normalized = structure.copy()
        normalized_sites = []
        for site in normalized:
            fcoords = [float(coord % 1.0) for coord in site.frac_coords]
            normalized_sites.append((str(site.specie), fcoords))

        lattice = normalized.lattice
        species = [item[0] for item in normalized_sites]
        coords = [item[1] for item in normalized_sites]
        normalized = Structure(lattice=lattice, species=species, coords=coords)
        normalized = self._deduplicate(normalized)

        atom_sites = [
            AtomSite(
                element=str(site.specie),
                x=float(site.frac_coords[0]),
                y=float(site.frac_coords[1]),
                z=float(site.frac_coords[2]),
            )
            for site in normalized
        ]

        lattice_dict = {
            "a": float(normalized.lattice.a),
            "b": float(normalized.lattice.b),
            "c": float(normalized.lattice.c),
            "alpha": float(normalized.lattice.alpha),
            "beta": float(normalized.lattice.beta),
            "gamma": float(normalized.lattice.gamma),
        }

        return ParsedStructure(
            lattice=lattice_dict, atoms=atom_sites, structure=normalized
        )

    def _deduplicate(self, structure: Structure, tolerance: float = 0.01) -> Structure:
        species: list[str] = []
        coords: list[list[float]] = []
        seen: set[tuple[str, int, int, int]] = set()
        scale = max(1, int(1 / tolerance))

        for site in structure:
            key = (
                str(site.specie),
                int(round(float(site.frac_coords[0]) * scale)),
                int(round(float(site.frac_coords[1]) * scale)),
                int(round(float(site.frac_coords[2]) * scale)),
            )
            if key in seen:
                continue
            seen.add(key)
            species.append(str(site.specie))
            coords.append([float(v) for v in site.frac_coords])

        return Structure(lattice=structure.lattice, species=species, coords=coords)
