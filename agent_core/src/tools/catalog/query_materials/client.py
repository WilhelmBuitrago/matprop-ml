from __future__ import annotations

import os
from pathlib import Path
from typing import List

from .errors import QueryAPIError, QueryValidationError
from .models import MaterialRecord, QueryRequest

_REQUIRED_FIELDS = (
    "material_id",
    "formula_pretty",
    "band_gap",
    "density",
    "is_stable",
    "is_metal",
    "energy_above_hull",
    "formation_energy_per_atom",
    "volume",
)


class MaterialsProjectClient:
    """Thin deterministic wrapper over mp_api MPRester."""

    def __init__(self) -> None:
        self._api_key = self._read_api_key()

    def query(self, request: QueryRequest) -> List[MaterialRecord]:
        mpr_cls = self._resolve_mpr_class()
        try:
            with mpr_cls(self._api_key) as mpr:
                if request.mode == "material_id":
                    docs = mpr.materials.summary.search(
                        material_ids=[request.value],
                        fields=list(_REQUIRED_FIELDS),
                    )
                elif request.mode == "formula":
                    docs = mpr.materials.summary.search(
                        formula=request.value,
                        fields=list(_REQUIRED_FIELDS),
                    )
                else:
                    docs = mpr.materials.summary.search(
                        chemsys=request.value,
                        fields=list(_REQUIRED_FIELDS),
                    )
        except Exception as exc:
            raise QueryAPIError(f"Materials Project API request failed: {exc}") from exc

        results: List[MaterialRecord] = []
        for doc in docs:
            normalized = self._normalize_doc(doc)
            if normalized is not None:
                results.append(normalized)
        return results

    def _resolve_mpr_class(self):
        try:
            from mp_api.client import MPRester  # type: ignore
        except Exception as exc:
            raise QueryAPIError("mp_api dependency is unavailable.") from exc
        return MPRester

    def _read_api_key(self) -> str:
        api_key = os.getenv("MP_API_KEY")
        if api_key:
            return api_key

        env_path = Path(__file__).resolve().parents[4] / ".env"
        if env_path.exists():
            api_key = self._read_api_key_from_env_file(env_path)
            if api_key:
                return api_key

        raise QueryValidationError("MP_API_KEY is missing in environment or .env file.")

    @staticmethod
    def _read_api_key_from_env_file(path: Path) -> str | None:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key.strip() != "MP_API_KEY":
                continue
            cleaned = value.strip().strip('"').strip("'")
            return cleaned or None
        return None

    @staticmethod
    def _normalize_doc(doc) -> MaterialRecord | None:
        material_id = getattr(doc, "material_id", None)
        formula = getattr(doc, "formula_pretty", None)
        band_gap = getattr(doc, "band_gap", None)
        density = getattr(doc, "density", None)
        is_stable = getattr(doc, "is_stable", None)
        is_metal = getattr(doc, "is_metal", None)
        energy_above_hull = getattr(doc, "energy_above_hull", None)
        formation_energy = getattr(doc, "formation_energy_per_atom", None)
        volume = getattr(doc, "volume", None)

        required_values = (
            material_id,
            formula,
            band_gap,
            density,
            is_stable,
            is_metal,
            energy_above_hull,
            formation_energy,
            volume,
        )
        if any(value is None for value in required_values):
            return None

        if not isinstance(is_stable, bool) or not isinstance(is_metal, bool):
            return None

        return MaterialRecord(
            material_id=str(material_id),
            formula=str(formula),
            band_gap=float(band_gap),
            density=float(density),
            is_stable=is_stable,
            is_metal=is_metal,
            energy_above_hull=float(energy_above_hull),
            formation_energy=float(formation_energy),
            volume=float(volume),
        )
