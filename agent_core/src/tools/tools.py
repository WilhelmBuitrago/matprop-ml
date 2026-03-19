from mp_api.client import MPRester
from typing import Dict, List, Union
import re
from pymatgen.core import Structure
import os

API_MP_KEY = os.getenv("MP_API_KEY")
if not API_MP_KEY:
    raise RuntimeError(
        "Missing required environment variable: MP_API_KEY (or legacy API_MP_KEY)"
    )

MP_ID_RE = re.compile(r"^mp-\d+$")
CHEMSYS_RE = re.compile(r"^[A-Z][a-z]?(-[A-Z][a-z]?)+$")
FORMULA_RE = re.compile(r"^[A-Z][a-z]?\d*([A-Z][a-z]?\d*)*$")
ALLOWED_FILTERS = {
    "band_gap": ("band_gap", "range"),
    "energy_above_hull": ("energy_above_hull", "range"),
    "formation_energy_per_atom": ("formation_energy_per_atom", "range"),
    "density": ("density", "range"),
    "volume": ("volume", "range"),
    "is_stable": ("is_stable", "bool"),
    "is_metal": ("is_metal", "bool"),
    "crystal_system": ("crystal_system", "enum"),
    "spacegroup_number": ("spacegroup_number", "int"),
    "nsites": ("nsites", "int"),
}


def normalize_filters(filters: dict) -> dict:
    if not isinstance(filters, dict):
        raise ValueError("filters must be a dict")

    kwargs = {}

    for key, raw_value in filters.items():
        if key not in ALLOWED_FILTERS:
            raise ValueError(f"Unsupported filter: {key}")

        mp_key, ftype = ALLOWED_FILTERS[key]

        if ftype == "range":
            if not isinstance(raw_value, dict):
                raise ValueError(f"{key} must be an object with min and max")

            if "min" not in raw_value or "max" not in raw_value:
                raise ValueError(f"{key} must contain min and max")

            lo = raw_value["min"]
            hi = raw_value["max"]

            if not all(isinstance(v, (int, float)) for v in (lo, hi)):
                raise ValueError(f"{key} min/max must be numeric")

            if lo > hi:
                raise ValueError(f"{key} min cannot be greater than max")

            kwargs[mp_key] = (float(lo), float(hi))

        elif ftype == "bool":
            if not isinstance(raw_value, bool):
                raise ValueError(f"{key} must be boolean")

            kwargs[mp_key] = raw_value

        elif ftype == "int":
            if not isinstance(raw_value, int):
                raise ValueError(f"{key} must be integer")

            kwargs[mp_key] = raw_value

        elif ftype == "enum":
            if not isinstance(raw_value, str):
                raise ValueError(f"{key} must be string")

            kwargs[mp_key] = raw_value

        else:
            raise RuntimeError(f"Unhandled filter type: {ftype}")

    return kwargs


def normalize_material_query(material):
    if isinstance(material, int):
        return {"type": "material_id", "value": [f"mp-{material}"]}

    if isinstance(material, str):
        material = material.strip()

        if MP_ID_RE.match(material):
            return {"type": "material_id", "value": [material]}

        if material.isdigit():
            return {"type": "material_id", "value": [f"mp-{material}"]}

        if CHEMSYS_RE.match(material):
            return {"type": "chemsys", "value": material}

        if FORMULA_RE.match(material):
            return {"type": "formula", "value": material}

    if isinstance(material, list):
        results = [normalize_material_query(m) for m in material]
        types = {r["type"] for r in results}
        if len(types) != 1:
            raise ValueError("Mixed material input types are not allowed")
        return {
            "type": results[0]["type"],
            "value": [v for r in results for v in r["value"]],
        }

    raise ValueError("Unsupported material input")


class tool:
    def __init__(self):
        pass

    def execute(self, **kwargs):
        pass


class SearchMaterialsTool(tool):
    def __init__(self):
        super().__init__()

    def search_materials(self, query: Dict) -> List[Dict]:
        base = normalize_material_query(query.get("material"))
        extra_filters = normalize_filters(query.get("filters", {}))

        with MPRester(API_MP_KEY) as mpr:
            if base["type"] == "material_id":
                docs = mpr.materials.summary.search(
                    material_ids=base["value"], **extra_filters
                )

            if base["type"] == "formula":
                docs = mpr.materials.summary.search(
                    formula=base["value"], **extra_filters
                )

            if base["type"] == "chemsys":
                docs = mpr.materials.summary.search(
                    chemsys=base["value"], **extra_filters
                )

        materials = []
        for doc in docs:
            summary = {}
            summary["material_id"] = doc.material_id
            print(doc.material_id)
            summary["formula_pretty"] = doc.formula_pretty
            summary["chemsys"] = doc.chemsys
            summary["crystal_system"] = doc.symmetry.crystal_system.name
            summary["spacegroup"] = {
                "number": doc.symmetry.number,
                "symbol": doc.symmetry.symbol,
            }
            summary["density"] = doc.density
            summary["volume"] = doc.volume
            summary["nsites"] = doc.nsites
            summary["energy_above_hull"] = doc.energy_above_hull
            summary["formation_energy_per_atom"] = doc.formation_energy_per_atom
            summary["is_stable"] = doc.is_stable
            summary["is_metal"] = doc.is_metal
            summary["band_gap"] = doc.band_gap
            summary["efermi"] = doc.efermi
            materials.append(summary)
        return materials

    def execute(self, **kwargs):
        query = kwargs.get("query", {})
        return self.search_materials(query)


class GetMaterialPropertiesTool(tool):
    def __init__(self):
        super().__init__()
        self.search_tool = SearchMaterialsTool()

    def get_material_properties(self, query: Dict, propertys: List):
        materials = self.search_tool.search_materials(query)
        selected_properties = list(propertys)
        if "material_id" not in selected_properties:
            selected_properties.append("material_id")
        summary = {}
        identity = ["material_id", "formula_pretty", "chemsys", "nsites"]
        termodynamic = ["energy_above_hull", "formation_energy_per_atom", "is_stable"]
        crystallography = ["crystal_system", "spacegroup", "density", "volume"]
        electronic = ["is_metal", "band_gap", "efermi"]
        if materials:
            summary["identity"] = {
                key: materials[0][key] for key in identity if key in selected_properties
            }
            summary["termodynamic"] = {
                key: materials[0][key]
                for key in termodynamic
                if key in selected_properties
            }
            summary["crystallography"] = {
                key: materials[0][key]
                for key in crystallography
                if key in selected_properties
            }
            summary["electronic"] = {
                key: materials[0][key]
                for key in electronic
                if key in selected_properties
            }
            return summary
        else:
            return {"error": "Material not found"}

    def execute(self, **kwargs):
        query = kwargs.get("query", {})
        propertys = kwargs.get("propertys", [])
        return self.get_material_properties(query, propertys)


def visualize_material_structure(material: Union[str, int, Structure]):
    """
    Visualize the crystal structure of a material using pymatgen's StructureVisualizer.

    Args:
        material (Union[str, Structure]): The material identifier (e.g., "mp-149") or a pymatgen Structure object.

    Returns:
        str: A URL or file path to the generated visualization.
    """
    from pymatgen.vis.structure_chemview import quick_view

    if isinstance(material, (str, int)):
        with MPRester(API_MP_KEY) as mpr:
            normalized = normalize_material_query(material)
            if normalized["type"] != "material_id" or not normalized["value"]:
                raise ValueError("material must resolve to a valid material_id")
            structure = mpr.get_structure_by_material_id(normalized["value"][0])
    elif isinstance(material, Structure):
        structure = material
    else:
        raise ValueError(
            "material must be a material ID string or a pymatgen Structure object"
        )

    visualizer = quick_view(structure)

    return visualizer


if __name__ == "__main__":
    query = {
        "query": {"material": "Si", "filters": {"volume": {"min": 925, "max": 927}}}
    }
    tool = SearchMaterialsTool()
    result = tool.execute(**query)
    print(result)
    # query = "mp-149"
    # result = visualize_material_structure(query)

    # print(result)
