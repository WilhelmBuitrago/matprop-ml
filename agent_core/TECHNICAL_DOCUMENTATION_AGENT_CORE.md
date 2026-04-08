# Agent Core - Documentación Técnica

Documento técnico de referencia para implementación, operación y troubleshooting de `agent_core`.

---

## 1. Alcance

Este documento describe la implementación actual de `agent_core`:
- arquitectura híbrida con runtime `legacy` (v3) y runtime `planned` (v4),
- modos de ejecución `legacy` y `planned`,
- contratos internos críticos (policy/evaluator/loop/state),
- integración HTTP con `agents` (`/v2/*`),
- variables de entorno y ownership de modelos.

`DOCUMENTATION_AGENT_CORE.md` se mantiene como versión general/ejecutiva.

---

## 2. Arquitectura actual (visión técnica)

Componentes principales:
- `CompletionServiceV3` (`src/api/v3/service.py`): orquestación request->loop->respuesta final.
- runtime legacy:
  - `run_loop` (`src/api/v3/loop.py`): ciclo determinístico de ejecución.
  - `LegacyPolicyEngine` (`src/api/v3/policy.py`)
  - `Evaluator` (`src/api/v3/evaluator.py`): señal de suficiencia para stop gating.
- runtime planned:
  - `PlannedRuntimeV4` (`src/api/v4/service.py`)
  - `DeepSeekOneShotPlanner` (`src/api/v4/planner.py`)
  - `run_loop` (`src/api/v4/loop.py`)
  - `LoopEvaluatorV4` (`src/api/v4/evaluator.py`)
  - `TraceEmitter` (`src/api/v4/trace.py`)
- `ToolRegistry` (`src/tools/config.py`, `src/tools/base.py`): precondiciones + validación de contratos.
- `ContextBuilder` (`src/api/v3/context_builder.py`): consolidación final de evidencia para legacy.

Invariante:
- Existe una sola API pública (`POST /v3/completions`) y dos rutas internas de ejecución.
- `legacy` y `planned` usan loops distintos (v3 y v4, respectivamente).

---

## 3. Contrato de entrada/salida del endpoint

### 3.1 Request (`CompletionRequestV3`)
Archivo: `src/api/v3/scheme.py`

Campos:
- `query: str`
- `stream: bool = false`
- `temperature: float = 0.2`
- `max_tokens_for_response: int = 512`
- `max_iterations: int = 8` (`1..32`)
- `max_tool_calls: int = 8` (`1..32`)
- `max_context_tokens: int = 2048` (`256..8192`)
- `max_wall_time_ms: int = 30000` (`1000..120000`)

Nota de consistencia:
- `CompletionRequestV3` define el default contractual de `max_wall_time_ms=30000`.
- `BudgetState` mantiene `max_wall_time_ms=80000` como default interno de dataclass, pero en el flujo normal queda sobreescrito por el request al construir el estado en `CompletionServiceV3`.

### 3.2 Response (`CompletionResponseV3`)
Campos:
- `id`
- `object = "text_completion"`
- `choices`
- `usage`
- `metadata`

En modo streaming (`stream=true`), `CompletionServiceV3.stream_chat_events()` emite eventos SSE: `start`, `loop_done`, `final`.

Nota:
- Los eventos anteriores aplican al modo `legacy`.
- En modo `planned`, el stream incluye eventos del `TraceEmitter`: `tool_start`, `tool_result`, `evaluation`, `plan_modified` (opcional), `stop`, además de `start` y `final`.

---

## 4. Policy engines

## 4.1 Interfaz base
Archivo: `src/api/v3/policy_engine_base.py`

Contrato:
- `classify_intent(query: str) -> str`
- `decide(state: AgentState, registry: ToolRegistry) -> PolicyDecision`

`PolicyDecision` (en `policy.py`):
- `tool_name: str`
- `tool_arguments: Dict[str, Any]`
- `scores: Dict[str, float]`
- `reasoning: str`

## 4.2 Selección de engine
Archivo: `src/api/v3/policy_factory.py`

Regla:
- Actualmente `create_policy_engine(...)` retorna `LegacyPolicyEngine` siempre.
- El modo `planned` no se resuelve en `policy_factory`; se ejecuta por ruta dedicada en `CompletionServiceV3` (`_chat_planned` / `_stream_planned`) hacia runtime v4.

## 4.3 LegacyPolicyEngine
Archivo: `src/api/v3/policy.py`

Flujo de decisión legacy:
1. `classify_intent` por heurística keyword.
2. `_intent_candidates(intent)` mapea intención a candidatos iniciales.
3. filtro por `registry.can_run(name, state)`.
4. score determinístico por combinación de:
   - missing coverage,
   - information gain,
   - state compatibility,
   - costo de herramienta.
5. selección por `argmax`.
6. construcción determinística de argumentos (`_build_arguments`).

Pesos actuales (`WEIGHTS`):
- `missing_coverage = 0.45`
- `information_gain = 0.30`
- `compatibility = 0.20`
- `cost = 0.15`

Costos por herramienta (`TOOL_COST`) definidos en código para:
- `query_materials_database`
- `validate_material_constraints`
- `search_scientific_documents`
- `document_rag`
- `generate_crystal_structure`

## 4.4 Planned Runtime v4
Archivos: `src/api/v4/*` + integración en `src/api/v3/service.py`

Objetivo:
- Ejecutar modo `planned` con planner one-shot, validación local y loop tool-centric asincrónico.

Pipeline planned actual:
1. Construye catálogo de tools desde `ToolRegistry.as_schema_catalog()`.
2. Llama planner one-shot (`DeepSeekOneShotPlanner`) vía `POST /v2/completions` con prompt JSON estricto.
3. Valida localmente: parseo JSON, filtrado de tools inexistentes, coherencia mínima de plan.
4. Si el plan es inválido o vacío tras filtrado: fallback inmediato a `LegacyPolicyEngine`.
5. Ejecuta loop v4 (`run_loop`) con guards de presupuesto y cursor de plan.
6. Evaluador v4 emite `EvaluatorFeedback` estructurado y opcionalmente sugiere cambios (`PlanChange`).
7. Cambios de plan se aplican con restricciones: máximo 2 modificaciones, solo después del cursor.
8. Se persiste traza en disco en cada evento; SSE solo cuando `stream=true`.

---

## 5. Ranking semántico de herramientas (estado de implementación)

Archivo: `src/shared/nlp/vectorizers/embedding_cache.py`

`ToolEmbeddingCache` existe e implementa ranking por embeddings de descripciones de tools.

Estado actual:
- No está conectado al flujo principal del runtime `planned` (`src/api/v4/*`).
- Su uso activo hoy es como componente disponible para futuras extensiones, no como paso obligatorio del planificador v4.

---

## 6. Planner (integración con agents) y validación local

## 6.1 Planner client
Archivo: `src/api/v4/planner.py`

Clase: `DeepSeekOneShotPlanner`

Contrato de request hacia `agents`:
- endpoint: `{AGENTS_URL}/v2/completions`
- payload:
  - `history` (mensajes con prompt planner)
  - `model_name`
  - `temperature`
  - `max_tokens`

Comportamiento:
- ejecución one-shot (sin retry externo).
- parseo JSON robusto (objeto directo o bloque incrustado).
- normalización a `PlanStep(tool, target, purpose)`.
- fallback a legacy en `planner_request_failed`, `planner_invalid_json`, `planner_empty_after_filter`, `planner_incoherent`.

Nota:
- Existe un cliente legacy `QwenPlanner` en `src/api/v3/planner.py` que consume `/v2/planner`, pero no participa del flujo principal actual.

---

## 7. Evaluador en v3

Archivo: `src/api/v3/evaluator.py`

Rol:
- evaluar suficiencia de evidencia para decidir parada temprana.
- no selecciona herramienta, no modifica pesos, no ejecuta acciones.

Llamada remota:
- endpoint: `{AGENTS_URL}/v2/completions`
- payload: `history`, `temperature=0.1`, `max_tokens=300`

Contrato interno normalizado (`EvaluatorFeedback` en `state.py`):
- `verdict: "sufficient" | "insufficient"`
- `confidence: float [0,1]`
- `missing_information: List[str]`
- `risk_if_stop: "low" | "medium" | "high"`
- `can_answer: bool`
- `reasoning: str`

Fallback local en error:
- `verdict="insufficient"`
- `confidence=0.4`
- `missing_information=["additional_evidence"]`
- `risk_if_stop="high"`
- `can_answer=false`
- `reasoning="fallback_evaluation"`

---

## 8. Stop gating determinístico

Archivo: `src/api/v3/loop.py`

Threshold configurable:
- `AGENT_EVALUATOR_STOP_TAU`
- default técnico: `0.75`
- clamp a `[0.0, 1.0]`

Alcance:
- Este gating aplica al loop `legacy` v3.
- En modo `planned` v4, la decisión de parada depende de `LoopEvaluatorV4` (`feedback.stop`) y guards de presupuesto/plan.

Regla `should_stop(feedback, tau)`:
- `feedback.can_answer == true`
- `feedback.verdict == "sufficient"`
- `feedback.confidence >= tau`
- `feedback.risk_if_stop != "high"`

Si cumple -> `stop_reason="sufficient_evidence"`.

---

## 9. run_loop: orden exacto de ejecución

Archivo: `src/api/v3/loop.py`

Por iteración:
1. Verifica `state.can_continue()` (límites y estado de ejecución).
2. Incrementa `iterations_used`.
3. Solicita `policy.decide(...)`.
4. Stall detection:
   - si misma tool consecutiva, incrementa `stall_counter`
   - si `stall_counter >= 2` -> `stop_reason="stall_detected"`.
5. Valida input (`registry.validate_input`).
6. Ejecuta herramienta (`tool.execute(..., agent_state=state)`).
7. Si `result.status != success` -> stop por error de herramienta.
8. Valida output (`registry.validate_output`).
9. Registra `ToolExecutionRecord` y actualiza `tool_calls_used`.
10. Aplica `apply_tool_result` sobre estado.
11. Calcula `tools_available` + `next_planned_step` (predicción determinística).
12. Ejecuta `evaluator.evaluate(...)`.
13. Registra trayectorias de confianza/riesgo.
14. Evalúa `should_stop`.
15. Actualiza `context_tokens_used` con estimación aproximada de evidencia iterativa.

Término por presupuesto:
- `max_iterations`
- `max_tool_calls`
- `max_context_tokens`
- `max_wall_time_ms`

Otros stop reasons relevantes:
- `no_valid_tools_available`
- `stall_detected`
- `tool_input_validation_failed`
- `tool_output_validation_failed`
- `tool_execution_failed` o error code específico de herramienta
- `sufficient_evidence`
- `budget_exhausted` (fallback final)

---

## 10. AgentState y estructuras

Archivo: `src/api/v3/state.py`

`AgentState` contiene:
- identidad request (`request_id`, `query`, `intent`)
- presupuesto (`BudgetState`)
- evidencia acumulada:
  - `materials_found`
  - `documents`
  - `extracted_insights`
  - `constraints`
  - `properties_collected`
- trazabilidad:
  - `tool_calls`
  - `policy_trace`
  - `evaluator_feedback`
  - `confidence_trajectory`
  - `risk_trajectory`
  - `evaluation_trace`
- control de ejecución:
  - `execution_status`
  - `stop_reason`
  - `stall_counter`
  - `started_at_ms`
  - `final_answer`

`BudgetState` defaults en código:
- `max_iterations=8`
- `max_tool_calls=8`
- `max_context_tokens=2048`
- `max_wall_time_ms=80000`

Nota:
- en flujo normal, `CompletionRequestV3` sobreescribe estos límites con sus propios defaults/inputs.

---

## 11. Integración con agents y ownership de modelos

Regla de arquitectura:
- `agent_core` no decide modelos LLM específicos.
- selección de modelos se centraliza en servicio `agents` (`src/models/registry.py`).

`agent_core` consume capacidades por contrato HTTP:
- `POST {AGENTS_URL}/v2/completions` (final answer + evaluator backend)
- `POST {AGENTS_URL}/v2/insights` (document_rag extractor)
- `POST {AGENTS_SERVICE_URL}/v2/embeddings` (scoring semántico y retrieval)

Nota de uso real:
- El runtime principal (`legacy` + `planned`) usa `/v2/completions`.
- `/v2/planner` queda como compatibilidad en `src/api/v3/planner.py` (actualmente no conectado al path principal).

---

## 12. Variables de entorno (agent_core)

Archivo de referencia: `.env.example`

| Variable | Default | Uso principal |
|---|---|---|
| `UNPAYWALL_EMAIL` | vacío | downloader de papers (document_rag) |
| `MP_API_KEY` | vacío | Materials Project query tool |
| `SEMANTIC_SCHOLAR_API_KEY` | vacío | search docs provider |
| `CROSSREF_EMAIL` | vacío | search docs provider |
| `AGENTS_URL` | `http://agents:8003` | planner, completions, insights |
| `AGENTS_SERVICE_URL` | `http://agents:8000` | embeddings service |
| `CORS_ALLOW_ORIGINS` | `http://localhost:3000` | API CORS |
| `AGENT_POLICY_MODE` | `legacy` | selección de policy engine |
| `AGENT_EVALUATOR_STOP_TAU` | `0.75` | threshold de stop gating |
| `AGENT_TRACE_DIR` | `agent_core/data/traces` | persistencia de trazas |
| `AGENT_PLANNER_MODEL` | `deepseek-r1:8b` | modelo planner one-shot v4 |
| `AGENT_EVALUATOR_MODEL` | `yasserrmd/Qwen2.5-7B-Instruct-1M` | modelo evaluador v4 |

`AGENT_*_MODEL` se define en `agent_core` como configuración de request hacia `agents`.

---

## 13. Persistencia de trazas

Archivos:
- `src/api/v3/service.py` (`_persist_trace`) para modo `legacy`.
- `src/api/v4/trace.py` (`TraceEmitter._persist`) para modo `planned`.

Ruta:
- `{AGENT_TRACE_DIR}/{request_id}.json`

Contenido persistido (varía por modo):
- `legacy`: query, intent, stop_reason, execution_status, budget, tool_calls, policy_trace, evaluator_feedback, confidence/risk trajectory, materials/documents/insights, final_answer.
- `planned`: query, stop_reason, plan, budget, plan_modifications_used, trace de eventos, final_answer.

---

## 14. Riesgos y notas operativas actuales

1. Modo `planned` usa fallback a legacy para mantener continuidad si falla planificación local one-shot.
2. La calidad del plan inicial depende del prompt y catálogo de tools; coherencia mínima evita secuencias inviables básicas.
3. Stop gating depende de calidad de señal del evaluador; `AGENT_EVALUATOR_STOP_TAU` permite calibración conservadora/agresiva.

---

## 15. Checklist de verificación rápida

1. `AGENT_POLICY_MODE` configurado (`legacy|planned`).
2. `AGENTS_URL` y `AGENTS_SERVICE_URL` resolviendo servicios correctos.
3. `POST /v2/completions` disponible en `agents` (crítico para planner/evaluator/final answer).
4. Si se usa `document_rag`, verificar disponibilidad de `POST /v2/insights`.
5. Si se usa ranking híbrido/embeddings en tools, verificar `POST /v2/embeddings`.
6. `AGENT_EVALUATOR_STOP_TAU` definido según política de riesgo (aplica a legacy).
7. Herramientas registradas y contratos válidos en `ToolRegistry`.

---

**Última actualización:** Abril 7, 2026
**Versión:** v3.4
**Tipo de documento:** Técnico/Profundo
