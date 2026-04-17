# Agent Core v4 - Documentacion tecnica para desarrollo y mantenimiento

## 1. Alcance, objetivo y fuentes de verdad

Este documento describe el comportamiento implementado de `agent_core` en runtime `v4` con foco en ejecucion basada en evidencia, validacion de conocimiento y resiliencia determinista.

### 1.1 Alcance funcional documentado

- API HTTP expuesta por FastAPI.
- Endpoint publico `POST /v4/completions` en modo sincronico y streaming SSE.
- Runtime planificado con entry policy, planner, loop, evaluator, domain critic y generacion final.
- Contratos de request/response y modelos internos de estado.
- Presupuesto de contexto unificado por `max_context_tokens`.
- Resiliencia determinista por niveles 2/3/4.
- Observabilidad con trazas JSON por request y logging estructurado.

### 1.2 Fuentes de verdad (rutas canonicas)

- `agent_core/src/api/app.py`
- `agent_core/src/api/router.py`
- `agent_core/src/api/security.py`
- `agent_core/src/api/v4/router.py`
- `agent_core/src/api/v4/scheme.py`
- `agent_core/src/api/v4/service.py`
- `agent_core/src/api/v4/loop.py`
- `agent_core/src/api/v4/planner.py`
- `agent_core/src/api/v4/evaluator.py`
- `agent_core/src/api/v4/domain_critic.py`
- `agent_core/src/api/v4/context_budget.py`
- `agent_core/src/api/v4/confidence.py`
- `agent_core/src/api/v4/resilience_policy.py`
- `agent_core/src/api/v4/state.py`
- `agent_core/src/api/v4/contracts.py`
- `agent_core/src/api/v4/constants.py`
- `agent_core/src/api/v4/trace.py`
- `agent_core/src/api/v4/entry_policy.py`
- `agent_core/src/api/v4/plan_validator.py`
- `agent_core/src/api/v4/history_item.py`
- `agent_core/src/api/v4/truncation.py`
- `agent_core/src/api/v4/execution_state.py`
- `agent_core/src/api/v4/runtime_state.py`
- `agent_core/src/contracts/tool_result.py`
- `agent_core/src/infrastructure/logging.py`
- `agent_core/src/tools/config.py`
- `agent_core/src/tools/base.py`

## 2. Superficie publica y versionado observable

### 2.1 Rutas HTTP activas

- Router raiz: `agent_core/src/api/router.py`.
- Montaje de v4 con prefijo `/v4`.
- Endpoint principal: `POST /v4/completions` (`agent_core/src/api/v4/router.py`).

### 2.2 Comportamientos del endpoint

- Si `stream=false` (default), responde `CompletionResponseV4`.
- Si `stream=true`, responde `StreamingResponse` con `media_type="text/event-stream"` y cabeceras SSE.
- Aplica seguridad mediante dependencia `enforce_request_security`.

### 2.3 Versiones visibles

- `FastAPI(... version="4.0.0")` en `agent_core/src/api/app.py`.
- `metadata.runtime_version = "v4"` en `agent_core/src/api/v4/service.py`.

## 3. Arquitectura por componentes

### 3.1 Capa API

- `api/app.py`: app, CORS, middleware de logging/correlacion.
- `api/router.py`: composicion de routers.
- `api/v4/router.py`: endpoint y bridge a servicio.

### 3.2 Capa de seguridad

- `api/security.py`: API key opcional y rate limiting in-memory.

### 3.3 Capa de orquestacion runtime

- `api/v4/service.py`: flujo end-to-end, llamada final, armado de respuesta.
- `api/v4/loop.py`: control iterativo (budget -> tool -> evaluator -> branch).
- `api/v4/planner.py`: plan inicial + replans.
- `api/v4/evaluator.py`: evaluator de loop + integracion de domain critic.
- `api/v4/domain_critic.py`: cliente, normalizacion de entradas y parser de salida.
- `api/v4/resilience_policy.py`: decisiones deterministas de fallback.

### 3.4 Capa de estado, contratos y presupuesto de contexto

- `api/v4/state.py`: `AgentState`, `BudgetState`.
- `api/v4/contracts.py`: `Plan`, `PlanStep`, `EvaluatorFeedback`, `EvaluationResult`.
- `contracts/tool_result.py`: contrato unificado `ToolResult` cross-layer.
- `api/v4/context_budget.py`: fuente unica para estimacion/truncado por tokens.
- `api/v4/history_item.py`: historia tipada (`query`, `plan`, `tool_call`, `tool_result`, `evaluation`, `domain_critic`).

### 3.5 Capa de trazabilidad/observabilidad

- `api/v4/trace.py`: eventos de ejecucion y persistencia por request.
- `infrastructure/logging.py`: logging JSON con `request_id`.

### 3.6 Capa de herramientas

- `tools/config.py`: registro central.
- `tools/base.py`: contrato base y validacion schema.
- `api/v4/entry_policy.py`: seleccion de tools.

## 4. Contratos publicos (request/response)

Fuente: `agent_core/src/api/v4/scheme.py`.

### 4.1 Request `CompletionRequestV4`

| Campo | Tipo | Default | Restricciones |
|---|---|---|---|
| `query` | `str` | - | no vacio tras normalizacion |
| `stream` | `bool` | `False` | - |
| `temperature` | `float` | `0.2` | `0.0 <= x <= 2.0` |
| `max_tokens_for_response` | `int` | `512` | `32 <= x <= 4096` |
| `max_iterations` | `int` | `8` | `1 <= x <= 32` |
| `max_tool_calls` | `int` | `8` | `1 <= x <= 32` |
| `max_context_tokens` | `int` | `2048` | `256 <= x <= 8192` |
| `max_wall_time_ms` | `int \| None` | `None` | si existe: `1000 <= x <= 120000` |

`max_context_tokens` es fuente unica de verdad para planner, evaluator y domain critic via `ContextBudget` request-scoped.

### 4.2 Response `CompletionResponseV4`

| Campo | Tipo | Observaciones |
|---|---|---|
| `id` | `str` | hash por request |
| `object` | `str` | `text_completion` |
| `choices` | `list[dict]` | texto final |
| `usage` | `dict \| None` | tokens estimados con `ContextBudget.estimate_text_tokens` |
| `metadata` | `dict \| None` | estado operativo, evaluaciones y trazas |

## 5. Contratos internos principales

### 5.1 ToolResult unificado

Fuente: `agent_core/src/contracts/tool_result.py`.

`ToolResult` incluye:

- `status: "success" | "error"`
- `payload: dict`
- `error_code: str | None`
- `error_detail: str | None`
- `confidence: float` en `[0,1]`
- `is_synthetic: bool`
- `trace: str | None`
- `source: "db" | "paper" | "rag" | "llm" | "simulation"`
- `confidence_signals: dict[str, float]`

Reglas:

- `source="rag"` fuerza `is_synthetic=True`.
- Se exponen propiedades de compatibilidad (`raw_output`, `structured_output`, `error_message`).

### 5.2 Evaluacion

`EvaluationResult` (`api/v4/contracts.py`) incluye:

- `stop`, `modify_plan`, `constraints_ok`, `reason`
- `confidence`
- `domain_valid`, `domain_confidence`, `domain_issues`

Combinacion aplicada en evaluator:

- `stop = evaluator_stop AND domain_valid`
- `replan = evaluator_modify_plan OR NOT domain_valid`
- `confidence = min(evaluator_confidence, domain_confidence)`
- hard guard: si `domain_valid=False`, entonces `stop=False` y `replan=True`.

## 6. Confidence por tipo de fuente

Fuente: `agent_core/src/api/v4/confidence.py`.

- Deterministas (`db`, `paper`): clamp `[0.9, 1.0]` con `completeness` + `consistency`.
- RAG: formula exacta

`confidence = 0.5 * avg_similarity + 0.3 * agreement + 0.2 * coverage`

- LLM puro (`llm`): clamp `[0.3, 0.6]` con `structure_consistency` + `low_entropy`.
- Simulacion (`simulation`): `confidence = 1 - normalized_error`.

## 7. Domain critic

Fuente: `agent_core/src/api/v4/domain_critic.py` y `api/v4/evaluator.py`.

### 7.1 Input obligatorio enviado

- `user_query`
- `tool_results` normalizados (incluyen `confidence`, `source`, `trace`)
- `reasoning_steps` resumidos/truncados
- `draft_response`

### 7.2 Prompt de intencion

El prompt exige evaluar validez fisica/coherencia y responder formato:

- `VALID: <yes/no>`
- `CONFIDENCE: <0-1>`
- `ISSUES:` con lista.

### 7.3 Parsing y precedencia

- Parser extrae `valid` (bool), `confidence` (float), `issues` (list[str]).
- Regla critica aplicada: no puede existir cierre final con `domain_valid=False`.

### 7.4 Modo de activacion

`DOMAIN_CRITIC_MODE`:

- `always`
- `only_stop`

## 8. Resiliencia determinista (ejecutable)

Fuente: `agent_core/src/api/v4/resilience_policy.py`, `service.py`, `loop.py`.

### Nivel 2 (planner falla)

Condicion:

- excepcion en planner o plan invalido.

Accion:

- seleccion determinista por keyword:
  - `property_query` -> `query_materials_database`
  - `literature` -> pipeline `search_scientific_documents` + `document_rag`

### Nivel 3 (tools fallan)

Condicion:

- multiples fallos de tools o resultados vacios/invalidos acumulados.

Accion:

- fallback directo al modelo final en modo explicito (`final_model_direct_fallback`), con modelo por defecto `WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M`.

### Nivel 4 (fallo total)

Condicion:

- fallo en llamada al modelo final.

Accion:

- respuesta explicita de limitacion tecnica y metadata de resiliencia nivel 4.

## 9. Flujo del runtime v4

1. Request `POST /v4/completions`.
2. Inicializacion de estado + budget + trace emitter.
3. Entry policy selecciona catalogo de tools.
4. Planner produce plan; si falla, se recupera con resiliencia nivel 2.
5. Loop por pasos:
   - valida precondiciones y schemas,
   - ejecuta tool,
   - calcula confidence por fuente,
   - actualiza estado,
   - evaluator decide control,
   - domain critic valida fisica y puede forzar replan.
6. Si hay degradacion de tools, puede activarse nivel 3.
7. Generacion final; si falla, nivel 4.
8. Respuesta con `usage`, `metadata`, trazas y stop reasons.

## 10. Stop reasons y compatibilidad

Fuente: `api/v4/constants.py` y `api/v4/state.py`.

- Se mantiene razon canonica + mapping legacy para compatibilidad externa.
- `completed` mapea a `sufficient_evidence` en metadata legacy.

## 11. Truncamiento y contexto

Fuente: `api/v4/context_budget.py`.

- Estimacion por tokenizer (`shared.nlp.tokenizer.tokenize`), no heuristica `len(text)//4`.
- Truncamiento explicito prioriza items relevantes recientes.
- Aplica de forma consistente en planner/evaluator/domain critic y metricas de uso en response.

## 12. Herramientas y metadata de evidencia

Todos los tools catalogados retornan `ToolResult` con metadata de evidencia:

1. `query_materials_database` -> `source=db`, deterministic signals.
2. `validate_material_constraints` -> `source=db`, deterministic signals.
3. `search_scientific_documents` -> `source=paper`, deterministic signals.
4. `document_rag` -> `source=rag`, `is_synthetic=True`, `avg_similarity/agreement/coverage`.
5. `generate_crystal_structure` -> `source=llm`, `is_synthetic=True`, `structure_consistency/low_entropy`.

## 13. Observabilidad

- Logging JSON con `request_id`.
- Trace por request en `{AGENT_TRACE_DIR}/{request_id}.json`.
- Trace adicional de domain critic en `{request_id}.domain_critic.json`.

## 14. Limitaciones actuales verificables

1. La validez fisica depende de salida de un LLM critic; se mitiga con parser estricto y precedencia dura.
2. La clasificacion `property_query` vs `literature` es keyword-based y determinista (no semantica profunda).
3. No hay timeout global independiente por endpoint mas alla de timeouts configurados por llamada.

## 15. Estado de pruebas relevantes

Suites verificadas durante este refactor:

- `tests/test_loop_stop_gating.py`
- `tests/test_evaluator_boundaries.py`
- `tests/test_truncation.py`
- `tests/test_integration/test_loop_termination.py`
- `tests/test_integration/test_full_loop.py`
- `tests/test_tools/*/test_tool_comprehensive.py` (las cinco tools)
- `tests/test_resilience_policy.py`

Resultado observado en ejecuciones target:

- runtime/integration target: 11 passed.
- tools comprehensive target: 31 passed.
- evaluator/resilience additions: 8 passed.

---

Documento actualizado con base exclusiva en las fuentes listadas en la seccion 1.2.
