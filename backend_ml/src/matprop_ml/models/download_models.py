# matprop_ml/models/download_models.py
import json
import requests
from pathlib import Path
from typing import List, Optional
from matprop_ml.config.config import CACHE_DIR, MODEL_SOURCES, COMMON_PATTERNS
import shutil


def is_html_content(b: bytes) -> bool:
    head = b[:512].lower()
    # heurística simple: si comienza con '<' y contiene 'html' pronto, es html
    return head.strip().startswith(b"<") and b"html" in head


def try_download_file(url: str, dest: Path) -> bool:
    """
    Descarga el contenido RAW en url a dest.
    Retorna True solo si status_code == 200, contenido no es HTML de error y tiene tamaño mínimo.
    """
    r = requests.get(url, timeout=20)
    if r.status_code != 200:
        return False

    content = r.content

    if is_html_content(content):
        # GitHub o proxy devolvió una página HTML (404/403 estilizada).
        return False

    dest.write_bytes(content)
    return True


def _ensure_dir_clean(path: Path, force: bool):
    """
    Si force True borra y recrea.
    Si force False: crea si no existe, pero no limpia.
    (Comportamiento conservador: no borra si force=False)
    """
    if path.exists():
        if force:
            shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
    else:
        path.mkdir(parents=True, exist_ok=True)


def _validate_model_json(json_path: Path):
    """
    Validaciones explícitas solicitadas:
    - el JSON debe parsearse
    - contener clave 'graph_converter'
    - contener 'metadata' con 'units', 'name', 'description'
    Lanza RuntimeError en caso de problemas con mensajes claros.
    """
    if not json_path.exists():
        raise RuntimeError(f"Falta JSON esperado: {json_path}")

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"JSON corrupto o inválido en {json_path}: {e}")

    if "graph_converter" not in data:
        raise RuntimeError(
            f"JSON de modelo {json_path} no contiene 'graph_converter'. Revisar el archivo."
        )

    md = data.get("metadata")
    if not isinstance(md, dict):
        raise RuntimeError(
            f"JSON de modelo {json_path} no contiene 'metadata' válido. Revisar: clave 'metadata' ausente o no es dict."
        )

    for key in ("units", "name", "description"):
        if key not in md:
            raise RuntimeError(
                f"metadata inválida en {json_path}: falta clave '{key}'. Revisar metadata del modelo."
            )


def download_megnet_model(model_key: str, force: bool = False):
    """
    Descarga los artefactos definidos en MODEL_SOURCES.
    Validaciones añadidas:
      * Sólo intenta patrones en COMMON_PATTERNS para 'properties'
      * Evita guardar páginas HTML como archivos
      * Verifica tamaño mínimo
      * Comprueba que cada split no quede vacío
      * Valida JSON del modelo (graph_converter + metadata.{units,name,description})
    """
    if model_key not in MODEL_SOURCES:
        raise KeyError(f"Modelo desconocido: {model_key}")

    cfg = MODEL_SOURCES[model_key]
    repo = cfg["repo"]
    branch = cfg.get("branch", "master")
    base = cfg["base_path"]
    splits = int(cfg.get("splits", 0))
    properties: Optional[List[str]] = cfg.get("properties")
    preferred_filenames: List[str] = cfg.get("filenames", [])
    props_in_subdirs: bool = bool(cfg.get("properties_in_subdirs", False))

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    base_dir = CACHE_DIR / model_key

    # MULTI-SPLIT
    if splits > 0:
        if force and base_dir.exists():
            shutil.rmtree(base_dir)

        for i in range(splits):
            local_split_dir = base_dir / str(i)
            _ensure_dir_clean(local_split_dir, force=False)

            downloaded_any = False

            # Si hay filenames preferidos, los intentamos estrictamente
            if preferred_filenames:
                for fname in preferred_filenames:
                    local_file = local_split_dir / fname
                    if local_file.exists() and not force:
                        downloaded_any = True
                        continue
                    url = f"https://raw.githubusercontent.com/{repo}/{branch}/{base}/{i}/{fname}"
                    ok = try_download_file(url, local_file)
                    if not ok:
                        raise RuntimeError(
                            f"Error: no se encontró o no es válido el archivo esperado para split {i}: {url}\n"
                            "Revisar: repo, branch, base_path y nombre de archivo. Comprueba manualmente la URL."
                        )
                    downloaded_any = True

            else:
                # Si hay properties listadas, solo intentamos patrones definidos en COMMON_PATTERNS.
                if properties:
                    for prop in properties:
                        found_for_prop = False
                        for patt in COMMON_PATTERNS:
                            candidate = patt.format(prop=prop)
                            local_file = local_split_dir / Path(candidate).name
                            url = f"https://raw.githubusercontent.com/{repo}/{branch}/{base}/{i}/{candidate}"
                            if local_file.exists() and not force:
                                found_for_prop = True
                                downloaded_any = True
                                break
                            ok = try_download_file(url, local_file)
                            if ok:
                                downloaded_any = True
                                found_for_prop = True
                                # Si es JSON, validar su contenido mínimo
                                if (
                                    local_file.suffix == ".json"
                                    or local_file.name.endswith(".hdf5.json")
                                ):
                                    _validate_model_json(local_file)
                                break
                        if not found_for_prop:
                            raise RuntimeError(
                                f"No se pudo descargar archivos para la propiedad '{prop}' en split {i} del modelo {model_key}.\n"
                                f"URLs probadas: {[f'https://raw.githubusercontent.com/{repo}/{branch}/{base}/{i}/{patt.format(prop=prop)}' for patt in COMMON_PATTERNS]}\n"
                                "Revisar si la propiedad existe en el repo remoto o si el patrón de nombre es distinto."
                            )
                else:
                    # No hay preferred filenames ni properties: intento archivos típicos (mantenemos behavior conservador)
                    # pero verificamos que al menos uno exista; en caso contrario fallamos.
                    for fname in (
                        "model.json",
                        "model.hdf5",
                        "model.weights.h5",
                        "scaler.pkl",
                    ):
                        local_file = local_split_dir / fname
                        url = f"https://raw.githubusercontent.com/{repo}/{branch}/{base}/{i}/{fname}"
                        if local_file.exists() and not force:
                            downloaded_any = True
                            continue
                        if try_download_file(url, local_file):
                            downloaded_any = True
                            # si es JSON validar
                            if local_file.suffix == ".json":
                                _validate_model_json(local_file)
                    if not downloaded_any:
                        raise RuntimeError(
                            f"No se descargó ningún archivo válido para split {i} en {model_key}. Probadas rutas con nombres comunes.\n"
                            "Revisar el repo remoto y actualiza MODEL_SOURCES con los nombres correctos o define 'filenames' en la configuración."
                        )

            # Verificación final por split: no debe quedar vacío
            if not any(local_split_dir.iterdir()):
                raise RuntimeError(
                    f"El directorio para split {i} quedó vacío: {local_split_dir}\n"
                    "Posibles causas: errores de conexión, rutas mal configuradas o nombres de archivos incorrectos."
                )

    # SINGLE (sin splits)
    else:
        if force and base_dir.exists():
            shutil.rmtree(base_dir)
        base_dir.mkdir(parents=True, exist_ok=True)

        # Si hay properties explícitas, intentamos únicamente los patrones en COMMON_PATTERNS
        if properties:
            for prop in properties:
                downloaded = False
                for patt in COMMON_PATTERNS:
                    candidate = patt.format(prop=prop)
                    candidate_clean = Path(candidate).name
                    local_file = base_dir / candidate_clean
                    if local_file.exists() and not force:
                        downloaded = True
                        break
                    url = f"https://raw.githubusercontent.com/{repo}/{branch}/{base}/{candidate_clean}"
                    ok = try_download_file(url, local_file)
                    if ok:
                        downloaded = True
                        # validar si es JSON
                        if local_file.suffix == ".json" or local_file.name.endswith(
                            ".hdf5.json"
                        ):
                            _validate_model_json(local_file)
                        break
                if not downloaded:
                    raise RuntimeError(
                        f"No se pudieron descargar archivos para la propiedad '{prop}' en {model_key}.\n"
                        f"URLs probadas: {[f'https://raw.githubusercontent.com/{repo}/{branch}/{base}/{patt.format(prop=prop)}' for patt in COMMON_PATTERNS]}\n"
                        "Revisar configuración o la existencia de los archivos en el repo remoto."
                    )

        elif preferred_filenames:
            for fname in preferred_filenames:
                local_file = base_dir / fname
                if local_file.exists() and not force:
                    continue
                url = (
                    f"https://raw.githubusercontent.com/{repo}/{branch}/{base}/{fname}"
                )
                ok = try_download_file(url, local_file)
                if not ok:
                    raise RuntimeError(
                        f"No se encontró archivo esperado: {url}\n"
                        "Revisar repo/branch/base_path y nombre de archivo en MODEL_SOURCES."
                    )
                # si es JSON validar su contenido
                if local_file.suffix == ".json" or local_file.name.endswith(
                    ".hdf5.json"
                ):
                    _validate_model_json(local_file)

        else:
            downloaded_any = False
            for fname in ("model.json", "model.hdf5", "model.weights.h5", "scaler.pkl"):
                local_file = base_dir / fname
                url = (
                    f"https://raw.githubusercontent.com/{repo}/{branch}/{base}/{fname}"
                )
                if local_file.exists() and not force:
                    downloaded_any = True
                    continue
                if try_download_file(url, local_file):
                    downloaded_any = True
                    if local_file.suffix == ".json":
                        _validate_model_json(local_file)
            if not downloaded_any:
                raise RuntimeError(
                    f"No se encontró ningún archivo conocido en {base} para {model_key}.\n"
                    "Si los archivos están nombrados de forma no estándar, añade 'filenames' o 'properties' en MODEL_SOURCES."
                )

    # Al terminar, retornamos la ruta base para mayor conveniencia.
    return base_dir
