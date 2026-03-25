from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, Optional

QueryMode = Literal["material_id", "formula", "chemical_system"]


@dataclass(frozen=True)
class QueryRequest:
    mode: QueryMode
    value: str
    filters: Dict[str, object]
    ranking: Optional[Dict[str, object]]
    limit: int


@dataclass(frozen=True)
class MaterialRecord:
    material_id: str
    formula: str
    band_gap: float
    density: float
    is_stable: bool
    is_metal: bool
    energy_above_hull: float
    formation_energy: float
    volume: float


@dataclass(frozen=True)
class RankedMaterial:
    material: MaterialRecord
    score: float
