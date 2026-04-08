# Servicio Agents (Ollama Runtime)

## 1. Nombre del servicio
Agents Runtime API (v2)

## 2. Descripción
Servicio FastAPI que actúa como runtime local de modelos sobre Ollama para consumo interno del ecosistema matprop-ml.

Estado actual:
- Arquitectura pública consolidada en `v2`.
- Capa de servicios estandarizada en `V2RuntimeServices`.
- Exposición HTTP en puerto `8003`.

Capacidades principales:
- completions generales,
- evaluación/decisión estructurada,
- extracción de insights,
- planificación y validación de plan,
- embeddings,
- soporte de generación cristalina,
- endpoints operativos de salud e información.

## 3. Rol dentro del sistema
- Centralizar inferencia local con un cliente único (`OllamaClient`).
- Resolver selección de modelos vía variables de entorno en un único registry.
- Exponer contratos HTTP estables para `agent_core`.
- Cargar modelos requeridos al arranque (`download_models`).
- Mantener separación de responsabilidades:
  - `api/v2`: contrato HTTP
  - `api/v2/service.py`: orquestación runtime
  - `api/v2/models.py`: clases de modelo (prompt + parseo + validación)
  - `services/*`: servicios reutilizables
  - `models/registry.py`: ownership de selección de modelos

## 4. Arquitectura de alto nivel
- Framework: FastAPI
- Runtime de modelos: Ollama (`ollama` SDK Python)
- Versionado expuesto: `/v2`
- Arranque: lifespan definido en `api/v2/router.py`

Estructura relevante:
- `src/api/app.py`: inicializa FastAPI con lifespan v2
- `src/api/router.py`: monta únicamente router `v2`
- `src/api/v2/router.py`: rutas públicas v2
- `src/api/v2/scheme.py`: contratos Pydantic
- `src/api/v2/service.py`: `V2RuntimeServices` y wrappers por capacidad
- `src/api/v2/models.py`: `DecisionModel`, `EvaluatorModel`, `InsightsModel`, `PlannerModel`
- `src/services/ollama_client.py`: cliente único para chat/embeddings/list/pull
- `src/services/generation_service.py`: `ChatService`, `CifService`, `InfoService`
- `src/services/model_service.py`: `LoadModelsService`
- `src/models/registry.py`: resolución de modelos desde env

## 5. Endpoints expuestos (v2)

### 5.1 POST /v2/completions
Entrada (`CompletionRequest`):
- `history: List[Dict[str, str]]`
- `temperature: float = 0.7`
- `max_tokens: int = 512`
- `model_name: str | None = None` (override opcional)
- `stop_tokens: List[str] = []`

Flujo:
1. Router valida payload.
2. `runtime_services.chat.chat(...)` delega a `ChatService`.
3. `ChatService` usa `OllamaClient.chat(...)` con:
   - modelo por defecto `GENERATION_MODELS["final"]`, o
   - `model_name` si viene explícito.

Salida:
- string con `message.content`.

Errores:
- `503 runtime_services_unavailable`
- `503 chat_failed: ...`

### 5.2 POST /v2/decision
Entrada (`DecisionModelInput`):
- `query`, `intent`, `state_summary`, `tools_available`, `history`, `current_attempt`

Flujo:
1. Router valida payload.
2. `runtime_services.decision.call(...)` delega en `DecisionService`.
3. `DecisionService` usa `DecisionModel` con `EVALUATOR_MODEL`.
4. Parseo JSON estricto + validación Pydantic.

Salida (`DecisionModelOutput`):
- `action`, `tool_name`, `tool_arguments`, `confidence`, `reasoning`.

Errores:
- `503 decision_model_failed: ...`

### 5.3 POST /v2/evaluate
Entrada (`EvaluatorModelInput`):
- `query`, `tool_name`, `tool_result`, `expected_properties`, `query_intent`, `accumulated_context`

Flujo:
1. Router valida payload.
2. `runtime_services.evaluator.call(...)` delega en `EvaluatorService`.
3. `EvaluatorService` usa `EvaluatorModel` con `EVALUATOR_MODEL`.
4. Parseo JSON estricto + validación Pydantic.

Salida (`EvaluatorModelOutput`):
- `evaluation`, `confidence`, `reasoning`, `missing_properties`.

Errores:
- `503 evaluator_model_failed: ...`

### 5.4 POST /v2/insights
Entrada (`InsightRequest`):
- `query: str`
- `chunk: str`
- `title: str = ""`
- `section: str = ""`
- `page: int = 0`
- `max_tokens: int = 180`

Flujo:
1. Router valida payload.
2. `runtime_services.insights.extract_insights(...)` delega en `InsightsService`.
3. `InsightsService` usa `InsightsModel` con `INSIGHTS_MODEL`.
4. Parsea salida tolerando array JSON o claves `extracted_info`/`facts`.

Salida (`InsightResponse`):
- `{"insights": ["..."]}`

Errores:
- `503 insights_failed: ...`

### 5.5 POST /v2/planner
Entrada (`PlannerRequest`):
- `query: str`
- `state: Dict[str, Any] = {}`
- `candidate_tools: List[PlannerCandidateTool] = []`
- `max_steps: int` en `[1, 3]` (default 3)

Flujo:
1. Router valida payload.
2. `runtime_services.planner.build_plan(...)` delega en `PlannerService`.
3. `PlannerService` usa `PlannerModel` con `PLANNER_MODEL`.
4. Normaliza plan para conservar sólo steps válidos y herramientas permitidas.

Salida (`PlannerResponse`):
- `steps: List[PlanningStep]` con máximo 3 pasos.

Errores:
- `503 planner_failed: ...`

### 5.6 POST /v2/cif
Entrada (`CifRequest`):
- `compound_name: str`
- `max_tokens: int = 512`

Flujo:
1. Router valida payload.
2. `runtime_services.cif.get_cif(...)` delega en `CifService`.
3. `CifService` usa `GENERATION_MODELS["cif"]`.

Salida:
- `{"cif": "..."}`

Errores:
- `503 cif_failed: ...`

### 5.7 POST /v2/crystal/spec
Entrada (`CrystalSpecExtractionRequest`):
- `query: str`
- `deterministic_spec: Dict[str, Any] = {}`

Flujo:
1. Router valida payload.
2. `runtime_services.crystal_spec.extract(...)` delega en `CrystalSpecExtractionAgent`.
3. Se retorna objeto con `spec` completado.

Salida:
- `{"spec": {...}}`

Errores:
- `503 crystal_spec_failed: ...`

### 5.8 POST /v2/crystal/complete
Entrada (`CrystalCompletionRequest`):
- `system_message: str`
- `user_prompt: str`
- `temperature: float = 0.3`
- `max_tokens: int = 768`
- `stop_tokens: List[str] = []`
- `model_name: str | None = None`

Flujo:
1. Router valida payload.
2. `runtime_services.cif.generate_from_prompt(...)` usa `CifService`.

Salida:
- `{"raw_generation": "..."}`

Errores:
- `503 crystal_complete_failed: ...`

### 5.9 POST /v2/embeddings
Entrada:
- `texts: List[str]` (mínimo 1)

Flujo:
1. Router valida payload.
2. `runtime_services.embeddings.embed_texts(...)` delega en `EmbeddingsService`.
3. `EmbeddingsService` usa `OllamaClient.embed_batch(...)` con `EMBEDDING_MODEL`.
4. Verifica cardinalidad (`len(embeddings) == len(texts)`).

Salida:
- `{"embeddings": [[float, ...], ...]}`

Errores:
- `400` si lista vacía
- `500 Embedding service failed: ...`

### 5.10 GET /v2/info
Salida:
- metadata del runtime (`service`, `ChatService`, `policy_version`).

### 5.11 GET /v2/health
Salida:
- `{"status": "ok"}`

## 6. Capa de servicios estandarizada

### 6.1 Patrón de estandarización (service-model)
Para capacidades con lógica de prompting estructurado (`decision`, `evaluate`, `insights`, `planner`) se aplica un patrón uniforme:

1. Clase de modelo en `api/v2/models.py`:
   - construye prompt,
   - llama `OllamaClient.chat`,
   - extrae/normaliza JSON,
   - valida contra esquema Pydantic.
2. Wrapper de servicio en `api/v2/service.py`:
   - instancia la clase de modelo,
   - expone método estable (`call`, `build_plan`, etc.).
3. Router en `api/v2/router.py`:
   - valida request,
   - delega al wrapper,
   - mapea errores HTTP.

Resultado: cada servicio tiene su modelo explícito y una interfaz de runtime consistente.

### 6.2 V2RuntimeServices
`V2RuntimeServices` inicializa, con cliente Ollama compartido:
- `loader` (`LoadModelsService`)
- `chat` (`ChatService`)
- `cif` (`CifService`)
- `crystal_spec` (`CrystalSpecExtractionAgent`)
- `embeddings` (`EmbeddingsService`)
- `decision` (`DecisionService`)
- `evaluator` (`EvaluatorService`)
- `insights` (`InsightsService`)
- `planner` (`PlannerService`)
- `info` (`InfoService`)

### 6.3 OllamaClient
Punto único de acceso para:
- `chat(...)`
- `embed(...)`
- `embed_batch(...)`
- `list_model_names()`
- `pull_model(...)`

## 7. Registro de modelos y ownership
Fuente única: `src/models/registry.py`.

Modelos resueltos por env:
- `EMBEDDING_MODEL` (`AGENT_EMBEDDING_MODEL`)
- `EVALUATOR_MODEL` (`AGENT_EVALUATOR_MODEL`)
- `INSIGHTS_MODEL` (`AGENT_INSIGHTS_MODEL`, fallback a evaluator)
- `PLANNER_MODEL` (`AGENT_PLANNER_MODEL`, fallback a evaluator)
- `FINAL_MODEL` (`AGENT_FINAL_MODEL`)
- `CIF_MODEL` (`AGENT_CIF_MODEL`)

Compatibilidad:
- `GENERATION_MODELS = {"evaluator", "final", "cif"}`

Carga al arranque:
- `ALL_MODELS` incluye todos los modelos anteriores.
- `LoadModelsService.download_models()` intenta garantizar disponibilidad local al startup.

## 8. Binding de contratos HTTP para agent_core
Cuando `agent_core` llama endpoints de `agents`, la selección de modelo la decide este servicio por env:
- `POST /v2/planner` -> `AGENT_PLANNER_MODEL`
- `POST /v2/completions` -> `AGENT_FINAL_MODEL` (o override `model_name`)
- `POST /v2/insights` -> `AGENT_INSIGHTS_MODEL`
- `POST /v2/embeddings` -> `AGENT_EMBEDDING_MODEL`

Regla operativa:
- El ownership de selección de modelos está en `agents`, no en `agent_core`.

## 9. Flujo de arranque
1. FastAPI entra al lifespan v2.
2. Resuelve `keep_alive` (`AGENTS_OLLAMA_KEEP_ALIVE`, default `0s`).
3. Detecta disponibilidad GPU (`AGENTS_OLLAMA_PREFER_GPU`, `NVIDIA_VISIBLE_DEVICES`, `nvidia-smi -L`).
4. Instancia `V2RuntimeServices`.
5. Ejecuta `runtime_services.download_models()`.
6. Queda listo para atender `v2/*`.

## 10. Variables de entorno

### Runtime/GPU
- `AGENTS_OLLAMA_KEEP_ALIVE` (default `0s`)
- `AGENTS_OLLAMA_PREFER_GPU` (default `true`)
- `NVIDIA_VISIBLE_DEVICES` (opcional)

### Selección de modelos
- `AGENT_EVALUATOR_MODEL`
- `AGENT_INSIGHTS_MODEL`
- `AGENT_PLANNER_MODEL`
- `AGENT_FINAL_MODEL`
- `AGENT_CIF_MODEL`
- `AGENT_EMBEDDING_MODEL`

Nota:
- defaults y fallback se resuelven en `src/models/registry.py`.

## 11. Dependencias externas
- Ollama local (`ollama.chat`, `ollama.embeddings`, `ollama.list`, `ollama.pull`).
- Detección opcional por `nvidia-smi`.

## 12. Consumidores internos
Principal consumidor:
- `agent_core`.

Uso esperado desde `agent_core`:
- `/v2/completions`, `/v2/insights`, `/v2/embeddings`, `/v2/planner`, y en flujos legacy `/v2/decision`/`/v2/evaluate` según integración.

## 13. Concurrencia y política de memoria
- `keep_alive=0s` reduce retención de modelos en memoria.
- `embed_batch` se ejecuta secuencialmente sobre `embed`.
- El servicio no expone SSE público; responde request/response por endpoint.

## 14. Manejo de errores y observabilidad
- `OllamaClient` encapsula errores como `RuntimeError`.
- Router v2 mapea excepciones a `HTTP 503/500` por endpoint.
- Logs de startup incluyen keep_alive, preferencia GPU y detección efectiva.
- `GET /v2/health` habilita probes de orquestación.

## 15. Compatibilidad de versión
- `v1` no forma parte del contrato operativo actual.
- Contrato oficial vigente: `v2`.

## 16. Despliegue Docker (resumen)
- Imagen base de runtime Ollama.
- Startup esperado:
  1. `ollama serve`
  2. arranque API FastAPI
  3. validación/descarga de modelos faltantes

## 17. Resumen ejecutivo
- Servicio consolidado en v2.
- Estándar explícito servicio-modelo para capacidades agenticas.
- Ownership de modelos centralizado en agents.
- Contratos HTTP alineados para integración con agent_core.
