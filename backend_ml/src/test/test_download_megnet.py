import shutil
from pathlib import Path
from matprop_ml.models.download_models import (
    download_megnet_model,
    MODEL_SOURCES,
    CACHE_DIR,
)
import pytest


MODULE_CACHE_ATTR = "matprop_ml.models.download_models.CACHE_DIR"


@pytest.mark.parametrize(
    "model_key",
    [
        "mp-2019.4.1",
        "mf_2020",
    ],
)
def test_force_redownload(tmp_path, monkeypatch, model_key):
    # Aislar la cache por parámetro de test: cada ejecución tendrá su propia carpeta
    fake_cache = tmp_path / "models_cache" / model_key
    # asegurar carpeta vacía
    if fake_cache.exists():
        shutil.rmtree(fake_cache)
    fake_cache.mkdir(parents=True, exist_ok=True)

    # Redirigir la constante CACHE_DIR dentro del módulo al tmp_path aislado
    # monkeypatch.setenv("MATPROP_CACHE_DIR", str(fake_cache))  # opcional, si tu código lee env
    monkeypatch.setattr(MODULE_CACHE_ATTR, fake_cache, raising=True)

    # Primera descarga (no force)
    download_megnet_model(model_key, force=False)
    initial_files = list(fake_cache.glob("**/*"))

    assert (
        len(initial_files) > 0
    ), "La primera descarga no produjo archivos; revisa MODEL_SOURCES y la conectividad"

    # Guardar timestamps por nombre relativo
    before = {f.relative_to(fake_cache): f.stat().st_mtime for f in initial_files}

    # Segunda descarga con force=True (debe borrar y re-descargar)
    download_megnet_model(model_key, force=True)
    refreshed_files = list(fake_cache.glob("**/*"))

    assert len(refreshed_files) > 0, "La descarga con force no produjo archivos"

    after = {f.relative_to(fake_cache): f.stat().st_mtime for f in refreshed_files}

    # 1) los nombres de archivo deben coincidir
    assert set(before.keys()) == set(after.keys()), (
        "Los nombres de archivo antes y después no coinciden. "
        "Puede indicar que la descarga parcial produjo diferentes artefactos."
    )

    # 2) todos los timestamps deben ser mayores (archivos re-creados)
    for k in before.keys():
        assert (
            after[k] > before[k]
        ), f"El archivo {k} no fue re-descargado (timestamp no cambió)"
