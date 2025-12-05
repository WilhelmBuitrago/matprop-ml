# matprop_ml/config/config.py
from typing import Dict, Optional
from pathlib import Path
from typing import Dict


# Intento robusto de localizar la raíz del proyecto (donde está pyproject.toml o .git).
# Evita depender de parents[n] hardcodeado que puede introducir duplicados.
def find_project_root(
    start: Path = None, markers=("pyproject.toml", "setup.py", ".git")
) -> Path:
    start = start or Path(__file__).resolve()
    for p in (start, *start.parents):
        for m in markers:
            if (p / m).exists():
                return p
    # Fallback: subir dos niveles (comportamiento anterior), pero explícito y claro.
    return start.parents[2]


PROJECT_ROOT = find_project_root()

# Caché de modelos: si tu proyecto usa layout src/matprop_ml, apuntamos a esa ruta.
# Esto evita acabar con matprop_ml/matprop_ml/data/... por error.
# Preferimos la ruta dentro de src si existe, si no, usamos PROJECT_ROOT / "matprop_ml".
if (PROJECT_ROOT / "src" / "matprop_ml").exists():
    CACHE_DIR = PROJECT_ROOT / "src" / "matprop_ml" / "data" / "models_cache"
else:
    CACHE_DIR = PROJECT_ROOT / "matprop_ml" / "data" / "models_cache"

MODEL_SOURCES: Dict[str, Dict[str, object]] = {
    "mf_2020": {
        "repo": "davidtangGT/MEGNET",
        "branch": "master",
        "base_path": "mvl_models/mf_2020/pbe_gllb_hse_exp",
        "splits": 6,
        "properties": None,
        "filenames": ["best_model.hdf5", "best_model.hdf5.json"],
        "metadata": {"backend": "MEGnet"},
    },
    "mf_2020_disorder": {
        "repo": "davidtangGT/MEGNET",
        "branch": "master",
        "base_path": "mvl_models/mf_2020/pbe_gllb_hse_exp_disorder",
        "splits": 6,
        "properties": None,
        "filenames": ["best_model.hdf5", "best_model.hdf5.json"],
        "metadata": {"backend": "MEGnet"},
    },
    "mp-2019.4.1": {
        "repo": "davidtangGT/MEGNET",
        "branch": "master",
        "base_path": "mvl_models/mp-2019.4.1",
        "splits": 0,
        "properties": ["efermi", "formation_energy", "log10G", "log10K"],
        "filenames": [],
        "properties_in_subdirs": False,
        "metadata": {"backend": "MEGnet"},
    },
}

# patrones de nombres a probar por propiedad
COMMON_PATTERNS = [
    "{prop}.hdf5",
    "{prop}.hdf5.json",
]
