import json
import pytest
from pathlib import Path
from matprop_ml.models.download_models import download_megnet_model
from matprop_ml.models.registry import ModelRegistry
from matprop_ml.models.loader import ModelLoader
from matprop_ml.models.build_layout import save_layout_json
import shutil

MODULE_CACHE_ATTR = "matprop_ml.models.download_models.CACHE_DIR"
pytestmark = pytest.mark.network


@pytest.mark.parametrize(
    "model_key",
    [
        "mp-2019.4.1",
        "mf_2020",
    ],
)
def test_generate_layout(tmp_path, monkeypatch, model_key):
    # ------------------
    # Preparar cache temporal
    # ------------------
    fake_cache = tmp_path / "models_cache" / model_key
    # asegurar carpeta vacía
    if fake_cache.exists():
        shutil.rmtree(fake_cache)
    fake_cache.mkdir(parents=True, exist_ok=True)

    # Redirigir la constante CACHE_DIR dentro del módulo al tmp_path aislado
    # monkeypatch.setenv("MATPROP_CACHE_DIR", str(fake_cache))  # opcional, si tu código lee env
    monkeypatch.setattr(MODULE_CACHE_ATTR, fake_cache, raising=True)

    # ------------------
    # Descargar modelo
    # ------------------
    model_dir = download_megnet_model(model_key)
    assert model_dir.exists(), "El directorio del modelo no fue creado"

    # ------------------
    # Generar layout JSON
    # ------------------
    fake_path = tmp_path / "model_layout.json"
    layout_path = save_layout_json(fake_path, fake_cache)
    assert layout_path.exists(), "El layout JSON no fue creado"

    # ------------------
    # Validar contenido del layout
    # ------------------
    content = json.loads(layout_path.read_text())
    assert model_key in content, f"{model_key} no está registrado en el layout"

    entry = content[model_key]
    assert "splits" in entry["metadata"], "Falta la clave 'splits'"
    if model_key == "mp-2019.4.1":
        assert "files" in entry or "properties" in entry, "Falta información del modelo"


@pytest.mark.parametrize(
    "model_key",
    [
        "mp-2019.4.1",
        "mf_2020",
    ],
)
def test_model_loading(tmp_path, monkeypatch, model_key):
    # ------------------
    # Preparar cache temporal
    # ------------------
    fake_cache = tmp_path / "models_cache" / model_key
    # asegurar carpeta vacía
    if fake_cache.exists():
        shutil.rmtree(fake_cache)
    fake_cache.mkdir(parents=True, exist_ok=True)

    # Redirigir la constante CACHE_DIR dentro del módulo al tmp_path aislado
    # monkeypatch.setenv("MATPROP_CACHE_DIR", str(fake_cache))  # opcional, si tu código lee env
    monkeypatch.setattr(MODULE_CACHE_ATTR, fake_cache, raising=True)

    # ------------------
    # Descargar modelo
    # ------------------
    model_dir = download_megnet_model(model_key)
    assert model_dir.exists()

    # ------------------
    # Generar layout (ModelRegistry lo necesita)
    # ------------------
    fake_path = tmp_path / "model_layout.json"
    layout_path = save_layout_json(fake_path, fake_cache)
    assert layout_path.exists()

    # ------------------
    # Cargar registros
    # ------------------
    print(fake_path, fake_cache)
    registry = ModelRegistry.from_file(layout_path)
    print(registry.list_models())

    assert model_key in registry.models, f"{model_key} no fue encontrado en el registro"

    # ------------------
    # Intentar cargar el modelo
    # ------------------
    if model_key == "mp-2019.4.1":
        loaded = ModelLoader(model_key, submodel="efermi", registry=registry)
    elif model_key == "mf_2020":
        loaded = ModelLoader(model_key, registry=registry)

    assert loaded is not None, f"No se pudo cargar el modelo {model_key}"
