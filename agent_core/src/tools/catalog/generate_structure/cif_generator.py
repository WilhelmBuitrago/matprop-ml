"""Serializers for crystal structures."""

from __future__ import annotations

from typing import Any

try:  # pragma: no cover - environment-dependent optional dependency
    from pymatgen.io.cif import CifWriter
    from pymatgen.io.vasp import Poscar
except Exception:  # pragma: no cover - handled at runtime
    CifWriter = None  # type: ignore[assignment]
    Poscar = None  # type: ignore[assignment]


def structure_to_cif(structure: Any) -> str:
    """Serialize structure to CIF string."""
    if CifWriter is None:
        raise RuntimeError("pymatgen_not_installed")
    return str(CifWriter(structure))


def structure_to_poscar(structure: Any) -> str:
    """Serialize structure to POSCAR string."""
    if Poscar is None:
        raise RuntimeError("pymatgen_not_installed")
    return Poscar(structure).get_str()
