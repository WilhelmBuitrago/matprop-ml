# Agent Core - Documentacion General

## 1. Resumen
Agent Core expone una unica API publica para completions:
- `POST /v4/completions`

No existe superficie publica de versiones anteriores.
La implementacion usa:
- runtime `v4` como unico camino activo.

## 2. Objetivo del servicio
Responder consultas de materiales con un loop de herramientas controlado por presupuesto, trazabilidad y validacion de contratos.

Principios:
1. Seleccion de herramientas con control deterministico local.
2. Planner y evaluator externos unificados via `agents` en `/v2/planning-evaluator`.
3. Evaluador fuera del historial conversacional de usuario.
4. Redaccion final en una sola llamada al modelo.

## 3. Endpoint publico
### `POST /v4/completions`
Contrato de request:
- `query: str`
- `stream: bool = false`
- `temperature: float = 0.2`
- `max_tokens_for_response: int = 512` (rango: 32..4096)
- `max_iterations: int = 8`
- `max_tool_calls: int = 8`
- `max_context_tokens: int = 2048`
- `max_wall_time_ms: int | null = null`

Validaciones de request (v4.1 + hardening):
- `query` se normaliza con `strip()` y rechaza blanco.
- `query` tiene limite de longitud: 1..10000.
- `temperature` acotada a `0.0..2.0`.
- `max_tokens_for_response` acotado a `32..4096`.

Regla de wall-time:
- Si `max_wall_time_ms` es `null`, no hay corte por tiempo.
- Si se envia valor, el loop puede cortar por presupuesto temporal.

Contrato de response:
- `id`
- `choices[0].text`
- `usage`
- `metadata`

Metadata relevante:
- `policy_mode` (`planned`)
- `planner_status` y `planner_fallback_reason` (cuando aplica)
- `stop_reason`
- `iterations_count`, `tool_calls_count`

## 4. Flujo interno v4
1. Entry Policy selecciona top-k tools por embeddings.
2. Si embeddings falla, fallback por heuristica semantica ligera (BM25 + regex).
3. Planner llama `POST {AGENTS_URL}/v2/planning-evaluator` con `mode="plan"`.
4. Loop ejecuta tools y valida input/output.
5. Evaluator llama `POST {AGENTS_URL}/v2/planning-evaluator` con `mode="evaluate"`.
6. Stop solo cuando `stop=true` y `constraints_ok=true`.
7. Si `modify_plan=true`, puede replanear (maximo 2 replans).

## 5. Integracion con agents
Agent Core consume:
- `POST {AGENTS_URL}/v2/planning-evaluator` (plan + evaluate)
- `POST {AGENTS_URL}/v2/completions` (respuesta final)
- `POST {AGENTS_URL}/v2/insights`
- `POST {AGENTS_SERVICE_URL}/v2/embeddings`

## 6. Variables de entorno clave
- `AGENTS_URL=http://agents:8003`
- `AGENTS_SERVICE_URL=http://agents:8003`
- `AGENT_PLANNING_EVALUATOR_MODEL=deepseek-r1:8b`
- `AGENT_PLANNER_MODEL=deepseek-r1:8b`
- `AGENT_EVALUATOR_MODEL=deepseek-r1:8b`
- `AGENT_TRACE_DIR=agent_core/data/traces`

## 7. Streaming
Si `stream=true`, el endpoint `/v4/completions` emite SSE.
Eventos comunes:
- `start`
- `tool_start`
- `tool_result`
- `evaluation`
- `plan_modified` (opcional)
- `stop`
- `final`

## 8. Observabilidad
Cada request persiste traza en:
- `{AGENT_TRACE_DIR}/{request_id}.json`

Incluye plan, presupuesto, stop_reason, trace de ejecucion y respuesta final.

## 9. Inicio rapido
Instalacion:
```bash
cd agent_core/
pip install -r requirements.txt
cp .env.example .env
```

Ejecucion:
```bash
python -m src.api.app
```

Prueba basica:
```bash
curl -X POST http://localhost:8004/v4/completions \
  -H "Content-Type: application/json" \
  -d '{"query":"Find silicon with band gap > 1 eV"}'
```

## 10. Nota de versionado
- API publica actual: `v4`
- La implementacion expone una sola version publica activa.

## Seguridad Operacional (v4)

- `AGENT_AUTH_MODE=api_key` activa autenticacion por header en `/v4/completions`.
- Header por defecto: `X-API-Key` (configurable con `AGENT_API_KEY_HEADER`).
- Rate limiting configurable con:
  - `AGENT_RATE_LIMIT_ENABLED`
  - `AGENT_RATE_LIMIT_MAX_REQUESTS`
  - `AGENT_RATE_LIMIT_WINDOW_SECONDS`
- Seguridad se aplica por dependencia de endpoint (`Depends(enforce_request_security)`).
- Logging estructurado JSON con `request_id` propagado por header `X-Request-ID`.
- Nunca versionar `.env` con secretos reales.
- Rotar cualquier API key previamente expuesta.

## 11. Cambios operativos v1.0.0 (Major)

### 11.1 Estado tipado
- Se incorpora `ExecutionState` para control explicito de:
  - `iterations_used`
  - `tool_calls_used`
  - `replans_used`
- Se incorpora `RuntimeState` para estado global del plan:
  - cursor
  - estado por step
  - conteos de materiales/documentos/insights
  - motivo de stop canónico

### 11.2 Historia semantica controlada
- `HistoryItem` tipado con tipos validos:
  - `query`
  - `plan`
  - `tool_call`
  - `tool_result`
- Evaluator no se guarda como item de history.
- Truncamiento determinista por tokens para llamadas al evaluator.

### 11.3 Validacion formal de plan
- Planner usa validador fuerte de coherencia.
- Si plan invalido: fallback obligatorio a plan minimo determinista.

### 11.4 Contrato formal de evaluator y fallback
- Evaluator retorna contrato formal (`stop`, `modify_plan`, `constraints_ok`, `reason`).
- Si evaluator falla:
  - con resultados de tools -> final con contexto
  - sin resultados de tools -> final solo con query

### 11.5 Stop reasons duales (transicion)
- Interno/canonico: enum global de razones de stop.
- Externo/legacy: valores historicos mantenidos para compatibilidad.
- Metadata expone ambos (`stop_reason`, `stop_reason_canonical`).

### 11.6 Trazabilidad reproducible obligatoria
Cada trace JSON ahora incluye, como minimo:
- `query`
- `plan`
- `execution_state`
- `runtime_state`
- `history`
- `evaluations`
- `stop_reason`
- `final_answer`

## 12. Alineacion con plan de hardening Priority 1

Plan de referencia aplicado:
- `docs/superpowers/plans/2026-04-14-agent-core-priority1-hardening.md`

Estado documentado en este servicio:
- Contrato de seguridad: auth por API key + rate limiting configurable.
- Endurecimiento de request contract (`query`, `temperature`, `max_tokens_for_response`).
- Logging estructurado en runtime y middleware HTTP con correlacion por request_id.
- Variables de entorno de seguridad/logging en `.env.example`.
- Dependencias pinneadas en `requirements.txt`.

**Ultima actualizacion:** Abril 15, 2026  
**Version documento:** v1.1.0  
**Tipo:** General
