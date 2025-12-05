# backend_llm/src/config.py
from pathlib import Path

# Ruta base: carpeta donde está este archivo
BASE_DIR = Path(__file__).resolve().parent

# data/cache dentro de la misma carpeta
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"

# Crear carpetas si no existen
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_cache_path(*parts: str) -> Path:
    """Devuelve una ruta dentro de data/cache"""
    return CACHE_DIR.joinpath(*parts)
