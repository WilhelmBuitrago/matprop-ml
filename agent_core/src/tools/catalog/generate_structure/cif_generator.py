"""Serializers for crystal structures."""

from __future__ import annotations

from pymatgen.core import Structure
from pymatgen.io.cif import CifWriter
from pymatgen.io.vasp import Poscar


def structure_to_cif(structure: Structure) -> str:
    """Serialize structure to CIF string."""
    return str(CifWriter(structure))


def structure_to_poscar(structure: Structure) -> str:
    """Serialize structure to POSCAR string."""
    return Poscar(structure).get_str()
