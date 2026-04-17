# Agents - Documentacion Tecnica Determinista (Runtime v2)

## 1. Alcance y fuente de verdad

Este documento describe el comportamiento implementado actualmente en `agents` (v2), incluyendo el endpoint dedicado de domain critic.

Fuentes de verdad usadas:

- `agents/src/api/app.py`
- `agents/src/api/router.py`
- `agents/src/api/v2/router.py`
- `agents/src/api/v2/scheme.py`
- `agents/src/api/v2/service.py`
- `agents/src/api/v2/models.py`
- `agents/src/models/registry.py`
- `agents/src/models/__init__.py`
- `agents/src/services/ollama_client.py`
- `agents/src/services/generation_service.py`
- `agents/src/services/model_service.py`
- `agents/src/services/crystal_spec_extraction_agent.py`

## 2. Superficie publica vigente

- `POST /v2/completions`
- `POST /v2/decision`
- `POST /v2/planning-evaluator`
- `POST /v2/domain-critic`
- `POST /v2/insights`
- `POST /v2/embeddings`
- `POST /v2/cif`
- `POST /v2/crystal/spec`
- `POST /v2/crystal/complete`
- `GET /v2/info`
- `GET /v2/health`

## 3. Arquitectura operativa

### 3.1 Capas

1. HTTP (`api/v2/router.py`): valida request, mapea errores a HTTP.
2. Services (`api/v2/service.py`): wrappers por capacidad y dependencia compartida.
3. Model adapters (`api/v2/models.py`): prompt/parseo para outputs estructurados.
4. Runtime LLM (`services/ollama_client.py`): chat, embeddings, list, pull.
5. Config (`models/registry.py`): resolucion de modelos por entorno.

### 3.2 Ensamblado en runtime

`V2RuntimeServices` crea con un `OllamaClient` compartido:

- `loader`
- `chat`
- `cif`
- `crystal_spec`
- `embeddings`
- `decision`
- `planning_evaluator`
- `domain_critic`
- `insights`
- `info`

## 4. Lifespan y disponibilidad

En startup v2:

1. resuelve `AGENTS_OLLAMA_KEEP_ALIVE`
2. evalua preferencia/deteccion GPU
3. crea `V2RuntimeServices`
4. ejecuta `download_models()`

Si `runtime_services` no esta listo, endpoints de inferencia responden `503 runtime_services_unavailable`.

## 5. Contratos HTTP (Pydantic)

Fuente: `agents/src/api/v2/scheme.py`.

Contratos relevantes:

- `CompletionRequest`
- `DecisionModelInput` / `DecisionModelOutput`
- `PlanningEvaluatorRequest` / `PlanningEvaluatorOutput`
- `DomainCriticRequest` / `DomainCriticResponse`
- `InsightRequest` / `InsightResponse`
- `CifRequest`
- `CrystalSpecExtractionRequest`
- `CrystalCompletionRequest`

### 5.1 Domain critic contract

`DomainCriticRequest`:

- `user_query: str`
- `model_name: str | None`
- `prompt: str`
- `tool_results: list[dict]`
- `reasoning_steps: list[str]`
- `draft_response: str`

`DomainCriticResponse`:

- `response: str`

## 6. Especificacion funcional por endpoint

### 6.1 `POST /v2/planning-evaluator`

Endpoint dual:

- `mode="plan"`: produce pasos de plan.
- `mode="evaluate"`: produce control del loop (`stop`, `constraints_ok`, `modify_plan`, `feedback`).

Implementado en `PlanningEvaluatorModel` (`api/v2/models.py`).

### 6.2 `POST /v2/domain-critic`

Endpoint dedicado implementado en:

- route: `api/v2/router.py`
- service wrapper: `DomainCriticService` (`api/v2/service.py`)
- model adapter: `DomainCriticModel` (`api/v2/models.py`)

Comportamiento:

1. Construye prompt con la instruccion base + bloques serializados (`user_query`, `tool_results`, `reasoning_steps`, `draft_response`).
2. Ejecuta chat con temperatura `0.0`.
3. Retorna texto plano sin parsear en `DomainCriticResponse.response`.
4. Si salida vacia, aplica fallback determinista:
   - `VALID: no`
   - `CONFIDENCE: 0.0`
   - `ISSUES: - empty_domain_critic_response`

### 6.3 Resto de endpoints

- `POST /v2/completions`: generacion final general.
- `POST /v2/decision`: decision estructurada.
- `POST /v2/insights`: extraccion de hechos.
- `POST /v2/embeddings`: embeddings por lote.
- `POST /v2/cif`, `POST /v2/crystal/spec`, `POST /v2/crystal/complete`: capacidades cristalograficas.
- `GET /v2/info`, `GET /v2/health`: endpoints operativos.

## 7. Seleccion de modelos y ownership

Fuente: `agents/src/models/registry.py`.

Variables relevantes:

- `AGENT_BASE_MODEL`
- `AGENT_PLANNING_EVALUATOR_MODEL`
- `AGENT_EVALUATOR_MODEL`
- `AGENT_PLANNER_MODEL`
- `AGENT_INSIGHTS_MODEL`
- `AGENT_FINAL_MODEL`
- `AGENT_CIF_MODEL`
- `AGENT_EMBEDDING_MODEL`
- `AGENT_DOMAIN_CRITIC_MODEL`

Constantes derivadas:

- `PLANNING_EVALUATOR_MODEL`
- `DOMAIN_CRITIC_MODEL`
- `ALL_MODELS` (incluye domain critic para preload en startup)

`agents` mantiene ownership de resolucion efectiva de modelos para contratos v2.

## 8. Parseo robusto y normalizacion

Fuente: `agents/src/api/v2/models.py`.

- `_extract_json_dict`: usado en flujos con salida JSON estricta.
- `_safe_json`: usado en insights con fallback tolerante.
- `DomainCriticModel`: no parsea internamente a JSON; preserva texto estructurado requerido por consumer.

## 9. Failure modes actuales

1. Runtime Ollama no disponible o errores de inferencia -> `503` en endpoints de inferencia.
2. Salidas no JSON en planning/decision -> errores de parseo/model validation.
3. Domain critic con salida vacia -> fallback determinista de texto estructurado.
4. Embeddings con lista vacia -> `400`.

## 10. Restricciones y limites

- API publica limitada a `/v2/*`.
- `planning-evaluator.max_steps` acotado a `1..8`.
- embeddings por lote secuencial en `embed_batch`.
- sin SSE para completions en este servicio.

## 11. Integracion con agent_core

`agent_core` consume de `agents`:

- `POST /v2/planning-evaluator` para planner/evaluator.
- `POST /v2/domain-critic` para validacion fisica/coherencia.
- `POST /v2/completions` para respuesta final.

Esto habilita ejecucion basada en evidencia con doble validador en el runtime v4.

---

Documento actualizado con base exclusiva en las fuentes listadas en la seccion 1.
