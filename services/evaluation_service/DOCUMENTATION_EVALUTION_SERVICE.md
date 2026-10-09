# Documentacion Del Evaluation Service

## 1. Que Es Este Servicio

`evaluation_service` es un microservicio FastAPI que ejecuta datasets de evaluacion contra `agent_core`, calcula metricas de calidad y genera reportes persistidos para analisis y comparacion de regresiones.

Es la capa de evaluacion del proyecto y su responsabilidad es convertir casos de dataset en resultados medibles de ejecucion.

## 2. Objetivo Principal

El objetivo del servicio es ofrecer una forma reproducible, auditable y comparable de evaluar el comportamiento del agente.

Lo logra mediante:
- Validacion y normalizacion de datasets.
- Ejecucion repetida de cada caso contra `agent_core` (`/v3/completions`, modo SSE).
- Calculo de metricas por query y agregadas.
- Evaluacion de confiabilidad estadistica.
- Generacion de reportes JSON y HTML.
- Comparacion de dos runs con umbrales y reglas de fallo estricto.

## 3. Donde Encaja En El Sistema

Puntos principales de integracion:
- Fuente de entrada: payload de dataset de evaluacion enviado por clientes/UI.
- Backend de ejecucion: endpoint `POST /v3/completions` de `agent_core`.
- Cadena de inferencia efectiva: `evaluation_service -> agent_core -> agents` (sin capa intermedia `backend_llm`).
- Persistencia: almacenamiento local en `storage/runs`.
- Consumidores: frontend de evaluacion, checks de CI o flujos manuales de analisis.

En `docker-compose.yml` este servicio se expone como `evaluation-service` en el puerto `8010` por defecto.

## 4. Arquitectura Del Servicio

Archivos principales y responsabilidades:
- `app.py`: inicializacion de FastAPI, middleware CORS y montaje del router en `/v1`.
- `routes.py`: endpoints HTTP para health, validacion, run, obtencion de reportes y compare.
- `dataset_schema.py`: contrato del dataset con Pydantic, normalizacion, control de duplicados y resumen de validacion.
- `evaluator_runner.py`: orquesta ejecuciones repetidas de casos contra `agent_core` y escribe artefactos del run.
- `metrics.py`: calcula metricas de exito/herramientas/estabilidad/latencia y la logica de comparacion.
- `report_generator.py`: genera el `report.json` canonico y el `report.html` legible.

## 5. Flujo End-To-End De Ejecucion

1. El cliente envia `POST /v1/evaluations/run` con `{ dataset, config }`.
2. El servicio valida el dataset con `load_dataset()`.
3. Para cada caso, el servicio ejecuta `repeat_count` repeticiones contra `agent_core` en modo SSE.
4. El runner captura eventos por repeticion, secuencia de acciones, herramientas usadas, stop reason y metadata.
5. El servicio enriquece cada query con expectativas del dataset (`expected_behavior`, `expected_tools`, `expected_outcome_type`).
6. `compute_metrics()` calcula metricas por query y agregadas.
7. `assess_statistical_reliability()` determina si el run esta en estado ready, warning o blocked para comparacion.
8. `generate_reports()` escribe `report.json` y `report.html`.
9. El servicio persiste el payload del run y devuelve identificadores y rutas de reportes.

## 6. Endpoints De API

Prefijo base: `/v1`

### 6.1 GET /v1/health

Proposito:
- Health check de vida del servicio.

Respuesta:
```json
{ "status": "ok" }
```

### 6.2 POST /v1/datasets/validate

Proposito:
- Validar el esquema y reglas de negocio del dataset antes de ejecutar.

Request body:
- Objeto de dataset en crudo.

Comportamiento:
- Devuelve resumen de validacion si es valido.
- Devuelve `400` con detalles de validacion si es invalido.

### 6.3 POST /v1/evaluations/run

Proposito:
- Ejecutar una evaluacion completa del dataset.

Estructura del request body:
```json
{
  "dataset": { "...": "EvaluationDataset payload" },
  "config": { "...": "RunConfig payload" }
}
```

Comportamiento importante:
- Si la validacion falla, responde `400`.
- El run ejecuta todos los casos con `repeat_count`.
- Los artefactos se escriben en `storage/runs/<timestamp>_<run_id>/`.
- Se calculan y persisten metricas y reportes.

Estructura de respuesta:
```json
{
  "run_id": "<id>",
  "dataset_validation": {
    "cases_count": 0,
    "difficulty_distribution": {},
    "dataset_name": "...",
    "dataset_checksum": "..."
  },
  "statistical_reliability": {
    "status": "ready|warning|blocked",
    "issues": [],
    "warnings": []
  },
  "report_paths": {
    "json_path": ".../report.json",
    "html_path": ".../report.html"
  }
}
```

### 6.4 GET /v1/evaluations/{run_id}

Proposito:
- Recuperar el `run_payload.json` persistido de un run.

Errores:
- `404 run_not_found` si no existe el directorio o el payload del run.

### 6.5 GET /v1/evaluations/{run_id}/report.json

Proposito:
- Descargar el reporte JSON canonico.

Errores:
- `404 report_not_found` si no existe.

### 6.6 GET /v1/evaluations/{run_id}/report.html

Proposito:
- Descargar el reporte HTML renderizado.

Errores:
- `404 report_not_found` si no existe.

### 6.7 POST /v1/evaluations/compare

Proposito:
- Comparar dos reportes de run usando umbrales de metricas.

Request body:
```json
{
  "current_run_id": "run_a",
  "baseline_run_id": "run_b",
  "thresholds": {
    "success_rate": -0.02,
    "false_success_rate": 0.01,
    "loop_failures": 0.02,
    "latency_total": 0.10,
    "tool_calls_count": 0.15
  }
}
```

Notas:
- `thresholds` es opcional, se aplican valores por defecto si se omite.
- Compare puede devolver `blocked` si faltan metadatos de versiones requeridas.
- Existe regla de fallo estricto si `false_success_rate` aumenta respecto al baseline.

## 7. Contrato Del Dataset (Resumen Operativo)

El contrato completo esta documentado en `README.md` dentro de la misma carpeta.

En alto nivel:
- Campos de raiz: `dataset_name`, `min_dataset_size_for_compare`, `min_cases_per_difficulty`, `cases`.
- Requeridos por caso: `query`, `expected_behavior`, `expected_outcome_type`, `query_type`, `difficulty`, `weight`.
- Opcional por caso: `expected_tools` (por defecto `[]`).
- Valores enum:
  - `expected_outcome_type`: `sufficient | failure | partial`
  - `query_type`: `simple | multi-step | ambigua | error-case`
  - `difficulty`: `easy | medium | hard`

Las reglas de validacion incluyen:
- Restricciones de Pydantic (longitudes/rangos).
- Normalizacion de campos.
- Deteccion de duplicados por stable case id.
- Validacion de cobertura por dificultad.

## 8. Referencia De RunConfig

`RunConfig` controla reproducibilidad, comportamiento del modelo y limites de ejecucion.

Campos clave:
- Conectividad:
  - `agent_core_base_url` (default `http://agent-core:8004`)
  - `timeout_seconds` (>= 5)
- Trazabilidad de versiones (requeridos, no vacios):
  - `agent_version`
  - `policy_version`
  - `evaluator_version`
  - `tools_version`
- Muestreo/modelo:
  - `model` (default `unknown`)
  - `temperature` (0.0 a 2.0)
  - `top_p` (> 0.0 y <= 1.0)
  - `max_tokens` (>= 32)
- Limites de ejecucion:
  - `repeat_count` (>= 3)
  - `max_iterations`
  - `max_tool_calls`
  - `max_wall_time_ms`
  - `max_context_tokens`

## 9. Persistencia Y Artefactos Generados

Para cada run, el servicio escribe en:
- `storage/runs/<timestamp>_<run_id>/`

Archivos generados:
- `manifest_run.json`: metadatos del run y versiones.
- `dataset_snapshot.json`: dataset normalizado usado en la ejecucion.
- `per_query_results.jsonl`: resultados por query.
- `per_query_repeats.jsonl`: registros por repeticion.
- `errors.jsonl`: errores recolectados de ejecucion.
- `run_payload.json`: payload completo del run.
- `report.json`: reporte canonico de metricas.
- `report.html`: reporte visual.
- `metrics_report.json`: payload de metricas calculadas.

## 10. Resumen De Metricas

Las metricas calculadas incluyen:
- Calidad de resultado:
  - `success_rate`
  - `false_success_rate`
  - `fallback_rate`
  - `loop_failures`
- Comportamiento de herramientas:
  - `tool_efficiency`
  - `tool_misuse`
- Consistencia de razonamiento:
  - `reasoning_stability`
- Costo/rendimiento de ejecucion:
  - `iterations_count`
  - `tool_calls_count`
  - `reclassifications_count`
  - `latency_total`

Las metricas se producen en agregados weighted y unweighted.

## 11. Confiabilidad Y Puerta De Compare

Antes de comparar, el servicio evalua la confiabilidad estadistica:
- Tamano minimo del dataset.
- Minimo de casos por dificultad.
- Minimo de repeticiones por query.

Estados de confiabilidad:
- `ready`: valido para comparar.
- `warning`: usable, pero el dataset puede estar en limite.
- `blocked`: la comparacion no debe ejecutarse.

Adicionalmente, compare se bloquea si faltan metadatos de version requeridos.

## 12. Modelo De Manejo De Errores

Patrones comunes de errores HTTP:
- `400`:
  - Payload de dataset invalido.
  - Fallos de validacion del dataset.
- `404`:
  - Almacenamiento de runs no encontrado.
  - Run o reporte no encontrado.

Etiquetas de error del runner:
- `timeout`
- `invalid_response`
- `tool_failure`
- `reasoning_failure`
- `evaluator_failure`

## 13. Desarrollo Local

Desde `services/evaluation_service`:

1. Instalar dependencias:
```bash
pip install -r requirements.txt
```

2. Levantar servicio:
```bash
uvicorn app:app --host 0.0.0.0 --port 8010 --reload
```

3. Verificar health:
```bash
curl http://localhost:8010/v1/health
```

Nota:
- Para la ejecucion completa de runs, `agent_core` debe ser accesible desde `agent_core_base_url`.

## 14. Ejecucion Con Docker

Comportamiento del contenedor standalone (ver `Dockerfile`):
- Imagen base: `python:3.12-slim`
- Puerto expuesto: `8010`
- Comando de inicio: `uvicorn app:app --host 0.0.0.0 --port 8010`

Servicio en Compose:
- Nombre del servicio: `evaluation-service`
- Puerto host: `${EVAL_SERVICE_PORT:-8010}`
- Volumen: `./services/evaluation_service/storage/runs:/app/storage/runs`
- Dependencia: `agent-core`

## 15. Solicitudes Minimas De Ejemplo

### Validar dataset
```bash
curl -X POST http://localhost:8010/v1/datasets/validate \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_name": "smoke_set",
    "min_dataset_size_for_compare": 3,
    "min_cases_per_difficulty": 1,
    "cases": [
      {
        "query": "Buscar propiedades de mp-149",
        "expected_behavior": "Devolver propiedades del material con un resumen conciso",
        "expected_tools": ["search_materials", "get_material_properties"],
        "expected_outcome_type": "sufficient",
        "query_type": "simple",
        "difficulty": "easy",
        "weight": 1.0
      },
      {
        "query": "Busqueda de material con id inexistente",
        "expected_behavior": "Manejar la ausencia del material de forma correcta",
        "expected_tools": ["search_materials"],
        "expected_outcome_type": "failure",
        "query_type": "error-case",
        "difficulty": "medium",
        "weight": 1.2
      },
      {
        "query": "Consulta ambigua sobre estructuras de bismuto",
        "expected_behavior": "Pedir aclaracion o entregar una respuesta parcial",
        "expected_tools": ["search_materials"],
        "expected_outcome_type": "partial",
        "query_type": "ambigua",
        "difficulty": "hard",
        "weight": 1.5
      }
    ]
  }'
```

### Ejecutar evaluacion
```bash
curl -X POST http://localhost:8010/v1/evaluations/run \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": {
      "dataset_name": "smoke_set",
      "min_dataset_size_for_compare": 3,
      "min_cases_per_difficulty": 1,
      "cases": [
        {
          "query": "Buscar propiedades de mp-149",
          "expected_behavior": "Devolver propiedades del material con un resumen conciso",
          "expected_tools": ["search_materials", "get_material_properties"],
          "expected_outcome_type": "sufficient",
          "query_type": "simple",
          "difficulty": "easy",
          "weight": 1.0
        },
        {
          "query": "Busqueda de material con id inexistente",
          "expected_behavior": "Manejar la ausencia del material de forma correcta",
          "expected_tools": ["search_materials"],
          "expected_outcome_type": "failure",
          "query_type": "error-case",
          "difficulty": "medium",
          "weight": 1.2
        },
        {
          "query": "Consulta ambigua sobre estructuras de bismuto",
          "expected_behavior": "Pedir aclaracion o entregar una respuesta parcial",
          "expected_tools": ["search_materials"],
          "expected_outcome_type": "partial",
          "query_type": "ambigua",
          "difficulty": "hard",
          "weight": 1.5
        }
      ]
    },
    "config": {
      "agent_core_base_url": "http://localhost:8004",
      "timeout_seconds": 60,
      "agent_version": "1.0.0",
      "policy_version": "1.0.0",
      "evaluator_version": "1.0.0",
      "tools_version": "1.0.0",
      "model": "gpt-5.3-codex",
      "temperature": 0.0,
      "top_p": 1.0,
      "max_tokens": 512,
      "repeat_count": 3,
      "max_iterations": 6,
      "max_tool_calls": 6,
      "max_wall_time_ms": 20000,
      "max_context_tokens": 1024
    }
  }'
```

## 16. Notas Operativas

- Mantener `repeat_count >= 3` para metricas de estabilidad con sentido.
- Incluir todos los campos de version en `RunConfig`; compare se bloquea si falta alguno.
- Usar datasets balanceados (`easy|medium|hard`) para evitar bloqueos de confiabilidad.
- Preservar artefactos de run para auditoria y analisis de regresiones.
