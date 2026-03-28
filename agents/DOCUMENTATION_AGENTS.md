# Servicio Agents (Ollama Runtime)

## 1. Nombre del servicio
Agents Runtime API

## 2. Descripcion
Servicio FastAPI que actua como gateway local sobre Ollama para inferencia y utilidades de ciclo agentico.

Version actual:
- Arquitectura `v2` only (se elimino `v1`).
- Capa de servicios estandarizada y centralizada en `V2RuntimeServices`.
- API HTTP expuesta en puerto 8003.

Capacidades principales:
- completions generales para consumidores internos,
- decision/evaluacion estructurada para ciclos agenticos,
- extraccion de insights con endpoint dedicado,
- embeddings para ranking semantico,
- generacion CIF,
- endpoints operativos de salud y metadata.

## 3. Rol dentro del sistema
- Proveer runtime local de modelos para servicios internos.
- Centralizar llamadas a Ollama mediante un cliente unificado.
- Resolver bootstrapping de modelos en arranque.
- Exponer contratos HTTP estables para `agent_core`.
- Mantener separacion de responsabilidades:
  - `api/v2`: contrato HTTP,
  - `api/v2/service.py`: orquestacion de runtime,
  - `api/v2/models.py`: prompts/parseo JSON para decision y evaluacion,
  - `services/*`: implementaciones reutilizables,
  - `models/registry.py`: fuente unica de nombres de modelos.

## 4. Arquitectura de alto nivel
- Framework: FastAPI.
- Runtime de modelos: Ollama local (SDK Python `ollama`).
- Versionado: solo prefijo `/v2`.
- Arranque: lifespan de `v2`.

Estructura relevante:
- `src/api/app.py`: inicializa FastAPI con lifespan v2.
- `src/api/router.py`: monta unicamente `v2`.
- `src/api/v2/router.py`: endpoints publicos.
- `src/api/v2/service.py`: fabrica `V2RuntimeServices` (chat, cif, embeddings, decision, evaluator, insights).
- `src/api/v2/models.py`: `DecisionModel` y `EvaluatorModel` (parseo JSON robusto).
- `src/api/v2/scheme.py`: contratos Pydantic de requests/responses v2.
- `src/services/ollama_client.py`: cliente unico para chat/embeddings/list/pull.
- `src/services/generation_service.py`: ChatService, CifService, InfoService.
- `src/services/model_service.py`: LoadModelsService.
- `src/models/registry.py`: `EMBEDDING_MODEL`, `GENERATION_MODELS`, `ALL_MODELS`.

## 5. Endpoints expuestos (v2)

### 5.1 POST /v2/completions
Entrada (`CompletionRequest`):
- `history: List[Dict[str, str]]`
- `temperature: float = 0.7`
- `max_tokens: int = 512`

Flujo:
1. Router valida payload.
2. `runtime_services.chat.chat(...)` delega a `ChatService`.
3. `ChatService` usa `OllamaClient.chat(...)` con modelo de `GENERATION_MODELS["final"]`.

Salida:
- texto de respuesta (`message.content`) del modelo.

Errores:
- `503 runtime_services_unavailable` si runtime no esta listo.
- `503 chat_failed: ...` ante fallo de inferencia.

### 5.2 GET /v2/info
Flujo:
- Router delega a `runtime_services.info.get_info()`.

Salida esperada:
- `service`
- `ChatService.Model`
- `ChatService.Version`
- `policy_version`

### 5.3 GET /v2/health
Salida:
- `{"status": "ok"}`

Uso:
- probes de healthcheck de Docker Compose para el servicio `agents`.

### 5.4 POST /v2/cif
Entrada (`CifRequest`):
- `compound_name: str`
- `max_tokens: int = 512`

Flujo:
1. Router valida payload.
2. `runtime_services.cif.get_cif(...)` delega a `CifService`.
3. `CifService` usa `OllamaClient.chat(...)` con modelo `GENERATION_MODELS["cif"]`.

Salida:
- `{"cif": "..."}`

Errores:
- `503 runtime_services_unavailable`
- `503 cif_failed: ...`

### 5.5 POST /v2/embeddings
Entrada:
- `texts: List[str]` (minimo 1)

Flujo:
1. Router valida payload.
2. `runtime_services.embeddings.embed_texts(...)` usa servicio singleton del runtime.
3. `EmbeddingsService` mantiene orden de entrada.
4. Usa `OllamaClient.embed_batch(...)` con `EMBEDDING_MODEL`.
5. Verifica cardinalidad (`len(embeddings) == len(texts)`).

Salida:
- `{"embeddings": [[float, ...], ...]}`

Errores:
- `400` si lista invalida.
- `500 embedding service failed` en fallo de backend o respuesta invalida.

### 5.6 POST /v2/decision
Entrada (`DecisionModelInput`):
- query, intent, state_summary, tools_available, history, current_attempt.

Flujo:
1. Router valida payload.
2. `runtime_services.decision.call(...)` delega en `DecisionService`.
3. `DecisionService` usa `DecisionModel` con modelo `GENERATION_MODELS["evaluator"]`.
4. Parse de JSON estricto + validacion Pydantic.

Salida (`DecisionModelOutput`):
- `action`, `tool_name`, `tool_arguments`, `confidence`, `reasoning`.

Errores:
- `503 decision_model_failed: ...`

### 5.7 POST /v2/evaluate
Entrada (`EvaluatorModelInput`):
- query, tool_name, tool_result, expected_properties, query_intent, accumulated_context.

Flujo:
1. Router valida payload.
2. `runtime_services.evaluator.call(...)` delega en `EvaluatorService`.
3. `EvaluatorService` usa `EvaluatorModel` con `GENERATION_MODELS["evaluator"]`.
4. Parse de JSON + validacion Pydantic.

Salida (`EvaluatorModelOutput`):
- `evaluation`, `confidence`, `reasoning`, `missing_properties`.

Errores:
- `503 evaluator_model_failed: ...`

### 5.8 POST /v2/insights
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
3. `InsightsService` llama `OllamaClient.chat(...)` con `GENERATION_MODELS["evaluator"]`.
4. Se parsea salida JSON (array o keys `facts`/`extracted_info`).

Salida (`InsightResponse`):
- `{"insights": ["..."]}`

Errores:
- `503 insights_failed: ...`

Nota de compatibilidad:
- `agent_core` debe usar `/v2/insights` para extraccion de insights.
- `/v2/completions` queda para chat general (modelo final), no para insights.

## 6. Capa de servicios estandarizada

### 6.1 OllamaClient
Archivo:
- `src/services/ollama_client.py`

Responsabilidades:
- `chat(model, messages, options)`
- `embed(model, text)`
- `embed_batch(model, texts)`
- `list_model_names()`
- `pull_model(model_name)`

Caracteristicas:
- punto unico de acceso a Ollama,
- unifica manejo de errores (`RuntimeError`),
- usa `keep_alive` configurado por runtime.

### 6.2 GenerationService
Archivo:
- `src/services/generation_service.py`

Servicios:
- `ChatService`
- `CifService`
- `InfoService`

### 6.3 ModelService
Archivo:
- `src/services/model_service.py`

Servicio:
- `LoadModelsService`

Responsabilidad:
- asegurar disponibilidad local de todos los modelos en `ALL_MODELS`.

### 6.4 Runtime v2
Archivo:
- `src/api/v2/service.py`

Componentes:
- `resolve_keep_alive()`
- `V2RuntimeServices`
- `EmbeddingsService`
- `DecisionService`
- `EvaluatorService`
- `InsightsService`

`V2RuntimeServices` inicializa en forma coherente (cliente compartido):
- `OllamaClient`
- `LoadModelsService`
- `ChatService`
- `CifService`
- `EmbeddingsService`
- `DecisionService`
- `EvaluatorService`
- `InsightsService`
- `InfoService`

## 7. Registro de modelos
Fuente unica:
- `src/models/registry.py`

Definiciones:
- `EMBEDDING_MODEL = "mxbai-embed-large"`
- `GENERATION_MODELS = {"evaluator", "final", "cif"}`
- `ALL_MODELS = [EMBEDDING_MODEL] + generation_models`

Asignacion operativa en v2:
- `/v2/completions` -> `GENERATION_MODELS["final"]`
- `/v2/cif` -> `GENERATION_MODELS["cif"]`
- `/v2/decision` -> `GENERATION_MODELS["evaluator"]`
- `/v2/evaluate` -> `GENERATION_MODELS["evaluator"]`
- `/v2/insights` -> `GENERATION_MODELS["evaluator"]`

Reglas:
- no hardcodear nombres de modelo en routers.
- servicios consumen registry directa o indirectamente.

## 8. Flujo de arranque
1. FastAPI inicia con lifespan de `v2`.
2. Se resuelve `keep_alive` (`AGENTS_OLLAMA_KEEP_ALIVE`, default `0s`).
3. Se detecta disponibilidad GPU (`NVIDIA_VISIBLE_DEVICES` y/o `nvidia-smi -L`).
4. Se instancia `V2RuntimeServices`.
5. `LoadModelsService.download_models()` verifica y descarga faltantes.
6. Servicio queda listo para `v2/*`.

## 9. Dependencias externas
No consume otros microservicios HTTP del proyecto.

Dependencias externas reales:
- Ollama local via SDK Python `ollama`:
  - `ollama.chat`
  - `ollama.embeddings`
  - `ollama.list`
  - `ollama.pull`
- Comando de sistema:
  - `nvidia-smi -L` (deteccion GPU)

## 10. Consumidores internos del runtime
Principal consumidor:
- `agent_core`

Uso esperado:
- `POST http://agents:8003/v2/completions` para generacion general.
- `POST http://agents:8003/v2/decision` para politica de decision.
- `POST http://agents:8003/v2/evaluate` para evaluacion de resultados.
- `POST http://agents:8003/v2/insights` para extraccion RAG de facts.
- `POST http://agents:8003/v2/embeddings` para embeddings del pipeline hibrido.

Frontend:
- no consume `agents` directamente en flujo principal;
- consume `agent-core`, que a su vez consume `agents`.

## 11. Concurrencia, rendimiento y politica de memoria
- `keep_alive` configurable via `AGENTS_OLLAMA_KEEP_ALIVE`.
- default operativo actual: `0s`.

Impacto:
- menor retencion de memoria,
- posible incremento de latencia en requests sucesivos.

Nota:
- No se aplica timeout de aplicacion en las llamadas HTTP `agent_core -> agents` por requisito de negocio actual.

## 12. Manejo de errores
- Capa de cliente (`OllamaClient`): convierte errores de SDK a `RuntimeError`.
- Capa API (`v2/router.py`): mapea excepciones a `HTTP 503/500` con detalle por endpoint.
- Carga de modelos: errores por modelo quedan en log y no detienen el proceso completo.

## 13. Observabilidad
- Logs de startup:
  - keep_alive efectivo,
  - preferencia y deteccion de GPU.
- Logs por endpoint de decision/evaluacion/insights ante fallos.
- Health endpoint:
  - `GET /v2/health` para probes de orquestacion.

## 14. Variables de entorno
- `AGENTS_OLLAMA_KEEP_ALIVE`
  - politica de retencion de modelo en Ollama (`0s`, `5m`, etc.).

- `AGENTS_OLLAMA_PREFER_GPU`
  - `true/false`.

- `NVIDIA_VISIBLE_DEVICES`
  - soporte de deteccion/ejecucion con GPU en Docker.

Nota:
- `AGENTS_DECISION_MODEL` ya no participa en el wiring de runtime v2.
- La seleccion de modelos de decision/evaluacion/insights viene de `GENERATION_MODELS["evaluator"]` en registry.

## 15. Contratos y compatibilidad
Estado de versionado:
- `v1` eliminado del servicio `agents`.
- contrato oficial actual: `v2`.

Compatibilidad requerida en consumidores:
- cualquier consumidor que apunte a `/v1/*` debe migrar a `/v2/*`.
- para insights, usar `/v2/insights` en lugar de `/v2/completions`.

## 16. Despliegue (Docker)
- Base de imagen: `ollama/ollama:latest`.
- Dependencias Python: `fastapi`, `uvicorn`, `ollama`, `pydantic`, etc.
- Startup esperado:
  1. `ollama serve`
  2. pull de modelos requeridos
  3. `uvicorn api.app:app --host 0.0.0.0 --port 8003`

## 17. Streaming y SSE
Implementacion actual:
- no hay SSE publico en `agents`.
- endpoints responden payload unico por request.

`agent_core` puede usar streaming propio en su capa API, pero `agents` permanece como runtime sin SSE expuesto.

## 18. Resumen ejecutivo
- Servicio consolidado en `v2`.
- Runtime unificado en `V2RuntimeServices` con cliente Ollama compartido.
- Endpoints de decision/evaluacion/insights centralizados y coherentes con registry.
- Contratos HTTP claros para `agent_core`.
- Eliminada dependencia operativa de `v1`.
