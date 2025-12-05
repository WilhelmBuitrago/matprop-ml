# matprop_ml/apis/schemas.py
from pydantic import BaseModel, Field, model_validator
from typing import Dict, Any


class StructureData(BaseModel):
    lattice: Dict[str, Any]
    sites: list[Dict[str, Any]]

    @model_validator(mode="after")
    def check_fields(self):
        if "matrix" not in self.lattice:
            raise ValueError("La estructura debe incluir lattice.matrix")
        if not self.sites:
            raise ValueError("La estructura debe incluir sitios atómicos")
        return self


class StructureRequest(BaseModel):
    filepath: str | None = None
    structure: StructureData | None = None
    metadata: Dict[str, Any] | None = None

    @model_validator(mode="after")
    def check_exclusive_inputs(self):
        if not self.filepath and not self.structure:
            raise ValueError("Debe proveerse filepath o una estructura pymatgen.")
        if self.filepath and self.structure:
            raise ValueError("Solo uno entre filepath o estructura.")
        return self


class PredictionResponse(BaseModel):
    model_key: str
    properties: Dict[str, Dict[str, Any]]
    aggregate: Dict[str, Any] | None = None
    metadata: Dict[str, Any] | None = None
