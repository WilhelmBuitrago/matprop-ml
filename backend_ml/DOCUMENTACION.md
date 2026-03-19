# Backend ML - Documentacion tecnica

## 1. Nombre del servicio
Backend ML API

## 2. Descripcion
Servicio FastAPI para inferencia de propiedades de materiales usando modelos MEGNet y un registro de artefactos en cache.

## 3. Responsabilidad dentro del sistema
- Exponer endpoints de prediccion por estructura.
- Gestionar carga y cache de modelos.
- Publicar modelos disponibles (registro local + modelos MEGNet preentrenados).

## 4. Dependencias
### 4.1 Internas
- `matprop_ml.models.registry` para metadata y layout.
- `matprop_ml.models.loader` para carga de modelos.
- `matprop_ml.models.material_predictor` para inferencia.

### 4.2 Externas
- FastAPI, Pydantic, Requests.
- TensorFlow, Keras, MEGNet.
- Pymatgen, mp-api.

## 5. Requisitos del entorno
- Runtime: Python 3.10.
- Puerto expuesto: 8000.
- Variables de entorno: opcionales segun configuracion de cache/modelos.

## 6. Endpoints principales
- `POST /v1/predict/{model_key}`: predice desde `filepath` o `structure`.
- `GET /v1/models`: lista modelos del registry y de MEGNet.
- `GET /v1/health`: estado del servicio.

## 7. Actualizacion de arquitectura (2026-03-15)
- Concurrencia:
  - Se agrego lock en `PredictionService` para proteger `loaded_models` y evitar condiciones de carrera.
- Loader canonico:
  - Se consolido una sola clase `ModelLoader` en `models/loader.py` y se elimino duplicidad.
- Layout de modelos:
  - `build_layout.py` ahora preserva todos los artefactos por split en lugar de descartar submodelos.
- Estructura de paquete:
  - Se corrigio nombre de inicializacion de paquete a `__init__.py`.
- Tests:
  - Los tests que dependen de red quedaron marcados con `@pytest.mark.network`.
  - Se agrego `pytest.ini` con marker `network` para separar ejecuciones offline.
- Dependencias:
  - Se aplico pinning estricto en `requirements.txt` y `pyproject.toml`.

## 8. Ejecucion de pruebas
- Suite sin red: `pytest -m "not network"`
- Suite con red: `pytest -m "network"`

## 9. Observabilidad
- Logging via modulo `logging` en carga/layout de modelos.
- Healthcheck para orquestacion.
