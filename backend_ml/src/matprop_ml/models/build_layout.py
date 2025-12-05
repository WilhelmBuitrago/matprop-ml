import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from matprop_ml.config.config import CACHE_DIR, MODEL_SOURCES

logger = logging.getLogger(__name__)


def _is_numeric_dir(d: Path) -> bool:
    return d.is_dir() and d.name.isdigit()


def _list_hdf5_and_json_files(dirpath: Path) -> List[Path]:
    return [
        p
        for p in dirpath.iterdir()
        if p.is_file() and p.suffix.lower() in {".hdf5", ".json"}
    ]


def _pair_submodels(files: List[Path]) -> Dict[str, List[str]]:
    """
    Construye:
        submodel_name -> list[str filenames]

    Reglas resumidas:
      - Si hay X.hdf5 => base = X. Busca:
            base.json
            X.hdf5.json
      - .json solos también generan submodelos.
    """
    files_by_name = {p.name: p for p in files}
    submodels: Dict[str, List[str]] = {}

    # Primero procesar .hdf5
    for name in files_by_name:
        if name.lower().endswith(".hdf5"):
            base = name[:-5]  # remove .hdf5
            key = base
            submodels.setdefault(key, []).append(name)

            candidate1 = f"{base}.json"
            candidate2 = f"{name}.json"

            if candidate1 in files_by_name:
                submodels[key].append(candidate1)
            elif candidate2 in files_by_name:
                submodels[key].append(candidate2)

    # Procesar .json sueltos
    for name in files_by_name:
        if not name.lower().endswith(".json"):
            continue

        already_used = any(name in lst for lst in submodels.values())
        if already_used:
            continue

        key = name[:-5]
        submodels.setdefault(key, []).append(name)

    return submodels


def _safe_metadata(model_key: str) -> Dict:
    """
    Clona la metadata de MODEL_SOURCES y evita mutación accidental.
    """
    src = MODEL_SOURCES.get(model_key, {})
    md = src.get("metadata", {})
    return dict(md)  # shallow copy suficiente aquí


def build_layout(cache_dir: Optional[Path] = None) -> Dict[str, Dict]:
    if cache_dir is None:
        cache_dir = CACHE_DIR

    cache_dir = Path(cache_dir)
    if not cache_dir.exists():
        raise FileNotFoundError(f"CACHE_DIR no existe: {cache_dir}")

    layout: Dict[str, Dict] = {}

    for model_dir in sorted(cache_dir.iterdir(), key=lambda p: p.name):
        if not model_dir.is_dir():
            continue

        model_key = model_dir.name
        logger.debug(f"Procesando modelo: {model_key}")

        numeric_dirs = sorted(
            [d for d in model_dir.iterdir() if _is_numeric_dir(d)],
            key=lambda p: int(p.name),
        )

        metadata = _safe_metadata(model_key)

        if numeric_dirs:
            # MODELOS CON SPLITS
            splits = len(numeric_dirs)
            split_contents: Dict[str, Dict[str, List[str]]] = {}

            for d in numeric_dirs:
                logger.debug(f"  Analizando split: {d.name}")
                files = _list_hdf5_and_json_files(d)
                submodels = _pair_submodels(files)
                split_contents[d.name] = [k for k in submodels.values()][0]
            metadata["splits"] = splits

            layout[model_key] = {
                "path": str(model_dir.resolve()),
                "split_contents": split_contents,
                "metadata": metadata,
            }

        else:
            # MODELOS SIN SPLITS
            files = _list_hdf5_and_json_files(model_dir)
            submodels = _pair_submodels(files)

            metadata["splits"] = 0

            layout[model_key] = {
                "path": str(model_dir.resolve()),
                "root_submodels": {k: v for k, v in submodels.items()},
                "properties": list(submodels.keys()),
                "metadata": metadata,
            }

    return layout


def save_layout_json(
    target_file: Optional[Path] = None, cache_dir: Optional[Path] = None
) -> Path:

    if target_file is None:
        target_file = (
            Path(__file__).resolve().parents[2]
            / "matprop_ml"
            / "data"
            / "models_cache"
            / "model_layout.json"
        )

    layout = build_layout(cache_dir=cache_dir)

    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(json.dumps(layout, indent=2, ensure_ascii=False))

    logger.info(f"model_layout.json generado en: {target_file}")
    return target_file


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    save_layout_json()
