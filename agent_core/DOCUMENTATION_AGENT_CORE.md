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
- `max_tokens_for_response: int = 512`
- `max_iterations: int = 8`
- `max_tool_calls: int = 8`
- `max_context_tokens: int = 2048`
- `max_wall_time_ms: int | null = null`

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

**Ultima actualizacion:** Abril 7, 2026  
**Version documento:** v4.0  
**Tipo:** General