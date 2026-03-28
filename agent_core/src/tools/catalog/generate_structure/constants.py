"""Domain constants for crystal generation validation."""

from __future__ import annotations

DEFAULT_MIN_DISTANCE_ANGSTROM = 1.1

# Symmetric pair keys are normalized as tuple(sorted((el1, el2))).
MIN_DISTANCE_THRESHOLDS: dict[tuple[str, str], float] = {
    ("O", "O"): 2.2,
    ("Li", "O"): 1.8,
    ("Co", "O"): 1.8,
    ("Ni", "O"): 1.8,
    ("Mn", "O"): 1.8,
    ("Fe", "O"): 1.8,
    ("Ti", "O"): 1.8,
    ("Si", "O"): 1.6,
    ("Al", "O"): 1.7,
    ("Na", "O"): 2.0,
    ("K", "O"): 2.3,
    ("Cu", "Cu"): 2.1,
    ("Si", "Si"): 2.2,
}

LATTICE_KEYWORDS = {
    "fcc": "fcc",
    "face centered cubic": "fcc",
    "bcc": "bcc",
    "body centered cubic": "bcc",
    "cubic": "cubic",
    "hexagonal": "hexagonal",
    "tetragonal": "tetragonal",
    "orthorhombic": "orthorhombic",
    "monoclinic": "monoclinic",
    "triclinic": "triclinic",
    "rhombohedral": "rhombohedral",
    "trigonal": "trigonal",
}
