# Agent Core - Documentacion Tecnica Determinista (Runtime v4)

## 1. Alcance y fuente de verdad
Este documento especifica el comportamiento operativo actual de `agent_core` v4 sin agregar features.

Fuente de verdad implementada:
- `src/api/v4/service.py`
- `src/api/v4/loop.py`
- `src/api/v4/planner.py`
- `src/api/v4/evaluator.py`
- `src/api/v4/state.py`
- `src/api/v4/contracts.py`
- `src/tools/base.py`

Superficie publica vigente:
- `POST /v4/completions`

## 2. Definicion formal de execution_state

### 2.1 Concepto
`execution_state` es un objeto JSON enviado por `agent_core` a `/v2/planning-evaluator` para control interno del ciclo (planeacion/evaluacion). No persiste como clase propia dentro de `agent_core`; se construye por llamada.

### 2.2 Estructura JSON por modo

#### 2.2.1 Modo `plan` (plan inicial)
Usado por `DeepSeekOneShotPlanner.build_plan(...)`.

```json
{
   "feedback": ""
}
```

Reglas:
- Campo obligatorio en payload de `agent_core`: `feedback` (string).
- Inicializacion en plan inicial: `""`.
- En replan: contiene feedback textual del evaluator.

#### 2.2.2 Modo `evaluate`
Usado por `LoopEvaluatorV4.evaluate(...)`.

```json
{
   "iterations_used": 1,
   "tool_calls_used": 1,
   "replans_used": 0
}
```

Reglas:
- Campos obligatorios: `iterations_used`, `tool_calls_used`, `replans_used` (int).
- No se envian otros campos desde `agent_core`.

### 2.3 Inicializacion y actualizacion por iteracion
Inicializacion en runtime:
- `iterations_used = 0`
- `tool_calls_used = 0`
- `replans_used = 0`

Actualizacion en loop (`run_loop`):
1. Antes de ejecutar cada step del plan: `iterations_used += 1`.
2. Despues de invocar `_execute_tool(...)`: `tool_calls_used += 1`.
3. Si `modify_plan == true` y replan exitoso: `replans_used += 1`.
4. Limite de replans: `MAX_REPLANS = 2`.

### 2.4 Diferencia explicita vs `history` y vs `state`
- `execution_state`: contadores de control del loop y feedback de replan.
- `history`: secuencia conversacional/operativa serializada por roles (`system`, `user`, `assistant`, `tool`).
- `state` (payload externo): snapshot estructurado de alto nivel para evaluator/planner.
   Ejemplo en evaluator: `materials_count`, `documents_count`, `insights_count`, `plan_cursor`, `plan_steps`, `stop_reason`.

### 2.5 Ejemplo realista
Payload enviado a `/v2/planning-evaluator` en modo `evaluate` tras 2 iteraciones y 1 replan:

```json
{
   "mode": "evaluate",
   "query": "Find stable semiconductor candidates with band gap around 1 eV",
   "history": [
      {"role": "system", "content": "You are an external evaluator controller. You are not a conversational actor and must not produce user-facing answers."},
      {"role": "user", "content": "Find stable semiconductor candidates with band gap around 1 eV"},
      {"role": "assistant", "content": "{\"plan\":{\"steps\":[{\"tool\":\"query_materials_database\",\"target\":\"Si\",\"purpose\":\"Collect evidence\"}],\"cursor\":0,\"status\":\"active\"}}"},
      {"role": "assistant", "content": "{\"action\":\"use_tool\",\"tool_call\":{\"tool\":\"query_materials_database\",\"target\":\"Si\",\"purpose\":\"Collect evidence\"}}"},
      {"role": "tool", "content": "{\"tool_result\":{\"status\":\"success\",\"structured_output\":{\"materials\":[{\"material_id\":\"mp-149\",\"formula\":\"Si\"}]}}}"}
   ],
   "state": {
      "materials_count": 1,
      "documents_count": 0,
      "insights_count": 0,
      "plan_cursor": 0,
      "plan_steps": 1,
      "stop_reason": null
   },
   "plan": {
      "steps": [{"tool": "query_materials_database", "target": "Si", "purpose": "Collect evidence"}],
      "cursor": 0,
      "status": "active"
   },
   "execution_state": {
      "iterations_used": 2,
      "tool_calls_used": 2,
      "replans_used": 1
   },
   "max_steps": 1
}
```

## 3. Definicion precisa de constraints_ok

### 3.1 Significado operativo
`constraints_ok` indica si, segun evaluator, las restricciones necesarias para cerrar el loop ya se cumplen.

Regla de stop efectiva en `agent_core`:

```text
stop efectivo = feedback.stop == true AND feedback.constraints_ok == true
```

Si `stop=true` y `constraints_ok=false`, el loop no se detiene por suficiencia.

### 3.2 Quién lo evalua
- Planner: no evalua `constraints_ok`.
- Evaluator (`/v2/planning-evaluator` con `mode="evaluate"`): unica fuente de `constraints_ok`.

### 3.3 Tipos de constraints (hard/soft)
En runtime v4 no existe tipado formal hard/soft dentro de `agent_core`.

Implicacion:
- Cualquier taxonomia interna del evaluator debe colapsarse a un booleano final `constraints_ok`.
- `agent_core` no distingue ni pondera tipos de constraint; solo consume el booleano.

### 3.4 Ejemplos concretos
- `constraints_ok=true`: evidencia suficiente y consistente para responder.
- `constraints_ok=false`: faltan validaciones o evidencia para restricciones solicitadas.

### 3.5 Que ocurre cuando es false
- Nunca activa stop por suficiencia, aun si `stop=true`.
- El loop continua: replan si `modify_plan=true` y hay cupo; de lo contrario avanza cursor del plan.

## 4. Especificacion de uso de history

### 4.1 Roles exactos admitidos
Roles validos en historia enviada a modelos externos:
- `system`
- `user`
- `assistant`
- `tool`

No se usa rol `evaluator`.

### 4.2 Subconjunto que recibe cada componente

#### 4.2.1 Planner (plan inicial)
- `history=[]`.
- No recibe historial conversacional previo.

#### 4.2.2 Planner (replan)
- Recibe `history` construido por `LoopEvaluatorV4.build_history(state)`.
- Contenido exacto:
   1. `system`: mensaje de control del evaluator.
   2. `user`: `state.query`.
   3. `assistant`: plan actual serializado.
   4. Para cada `tool_start`: `assistant` con `{"action":"use_tool","tool_call":...}`.
   5. Para cada `tool_result`: `tool` con `{"tool_result":...}`.

#### 4.2.3 Evaluator
- Recibe exactamente el mismo formato producido por `build_history(state)`.

### 4.3 Estrategia de truncamiento
No existe truncamiento de `history` en v4.

Efecto:
- Se incluye toda la traza de eventos `tool_start` y `tool_result` acumulada en `state.execution_trace`.

### 4.4 Justificacion de diseno
- Evaluator y replan requieren contexto operativo de ejecucion (no solo chat) para decidir `stop`/`modify_plan`.
- Se omiten eventos no tool (`evaluation`, `stop`, `final`, etc.) para reducir ruido y evitar retroalimentacion circular.

## 5. Flujo de replanificacion (modify_plan)

### 5.1 Trigger
Se activa replan cuando:
- `feedback.modify_plan == true`
- `state.replans_used < 2`

### 5.2 Feedback enviado al planner
En replan, `agent_core` envia solo:
- `feedback`: texto libre `feedback.feedback`

Se inyecta en payload como:

```json
"execution_state": {
   "feedback": "<feedback textual del evaluator>"
}
```

### 5.3 Que se excluye explicitamente
No se envia al planner en `execution_state` de replan:
- `stop`
- `constraints_ok`
- `modify_plan`
- metadatos de score/confianza del evaluator (no existen en contrato consumido)

### 5.4 Prevencion de leakage/ruido
- El planner recibe historial operativo filtrado (solo eventos de tools) y feedback textual corto.
- No recibe eventos `evaluation` previos ni respuesta final al usuario.

### 5.5 Limite de replans e impacto en estado
- Limite fijo: `MAX_REPLANS = 2`.
- Si se alcanza el limite:
   - se ignora `modify_plan=true` posterior,
   - el loop continua con `state.plan.cursor += 1` sobre el plan vigente.
- Cada replan exitoso:
   - reemplaza `state.plan` completo,
   - incrementa `state.replans_used`.

## 6. Especificacion de ejecucion de tools

### 6.1 Formato de entrada a tools
Cada step del plan tiene:

```json
{
   "tool": "<tool_name>",
   "target": "<optional>",
   "purpose": "<non-empty>"
}
```

`agent_core` transforma `tool+target+state` en argumentos de ejecucion por `_build_tool_arguments(...)`.

Ejemplos:
- `query_materials_database`: `{"material_id": "mp-149", "filters": {}, "limit": 5}` o `{"formula": "Si", ...}`.
- `validate_material_constraints`: `{"constraints": ...}`.
- `search_scientific_documents`: `{"query": state.query, "material_focus": ..., "max_results": 5}`.

Validacion previa:
- `ToolRegistry.validate_input(tool_name, arguments)` contra `input_schema`.

### 6.2 Formato de salida de tools
Contrato normalizado interno en loop:

```json
{
   "status": "success|error",
   "raw_output": {},
   "structured_output": {},
   "error_message": "...|null"
}
```

La salida nativa de herramienta (`tools.base.ToolResult`) se convierte a este contrato.

Validacion posterior:
- `ToolRegistry.validate_output(tool_name, payload)` contra `output_schema`.

### 6.3 Serializacion en history (rol tool)
- `tool_start` se serializa como `assistant`:

```json
{"action": "use_tool", "tool_call": {...}}
```

- `tool_result` se serializa como `tool`:

```json
{"tool_result": {...}}
```

### 6.4 Efecto sobre execution_state
- Cada invocacion de `_execute_tool(...)` incrementa `tool_calls_used`.
- Cada paso de loop incrementa `iterations_used`.
- Replan exitoso incrementa `replans_used`.

### 6.5 Manejo de errores de tools
Errores manejados por `agent_core`:
- Input invalido por schema -> `status=error`.
- Excepcion de ejecucion (incluye timeouts internos de la herramienta, si la herramienta los lanza) -> `status=error`.
- Salida invalida por schema -> `status=error`.
- Tool reporta `status != success` -> `status=error`.

Comportamiento del loop ante error:
- `state.stop_reason = "tool_execution_failed"`
- emision de evento `stop`
- terminacion inmediata del loop.

Nota operativa:
- `agent_core` no aplica timeout externo global por tool call en `run_loop`; depende del comportamiento de la herramienta.

## 7. Contrato interno asumido de /v2/planning-evaluator (subset consumido)

No redefine el contrato completo; documenta solo lo que `agent_core` usa.

### 7.1 Campos consumidos obligatoriamente
- `plan` (semantica de salida de plan): consumido como lista de `steps` y convertido a `Plan` interno.
- `stop` (modo evaluate).
- `constraints_ok` (modo evaluate; fallback a `stop` si no viene).
- `modify_plan` (modo evaluate).

### 7.2 Suposiciones criticas
- Estructura JSON parseable y tipo objeto.
- Coherencia minima de pasos: tools validos y secuencia coherente (validada por `is_plan_coherent`).
- Determinismo parcial esperado: mismas entradas tienden a producir señales de control compatibles, pero no se asume determinismo estricto del modelo.
- Si falta `constraints_ok`, se asume `bool(stop)` por fallback defensivo.

## 8. Separacion de responsabilidades

### 8.1 history (contexto conversacional/operativo)
- Formato de mensajes por rol para consumo de modelos.
- Incluye query, plan serializado y eventos de herramientas.
- No es fuente de verdad estructural del runtime.

### 8.2 execution_state (control del proceso)
- Contadores y feedback puntual para plan/evaluate.
- Enfocado en gobernanza de loop, no en contenido cientifico.

### 8.3 state (snapshot estructurado)
- Resumen estructurado de estado del agente para evaluator/planner.
- En evaluator: conteos y posicion de plan.
- En planner inicial: contexto de entry policy.

### 8.4 Anti-patrones (NO hacer)
- No usar `history` como datastore de estado estructurado persistente.
- No inferir stop solo con `stop=true`; siempre requiere `constraints_ok=true`.
- No enviar eventos `evaluation` al planner para replan (introduce bucle de ruido).
- No mezclar metadata de respuesta final de usuario dentro de `execution_state`.

## 9. Ejemplo end-to-end completo del loop

Escenario: consulta de semiconductor estable.

### 9.1 Query de entrada

```json
{
   "query": "Busca un semiconductor estable con band gap cercano a 1 eV"
}
```

### 9.2 Plan inicial (mode=plan)
Respuesta del servicio planning-evaluator (subset util):

```json
{
   "steps": [
      {
         "action": "use_tool",
         "tool": "query_materials_database",
         "input": {"formula": "Si"},
         "purpose": "Recolectar candidatos estables"
      },
      {
         "action": "use_tool",
         "tool": "validate_material_constraints",
         "input": {},
         "purpose": "Verificar restricciones solicitadas"
      },
      {
         "action": "respond",
         "purpose": "Responder con evidencia"
      }
   ]
}
```

`agent_core` normaliza a `PlanStep` y descarta `respond` para ejecucion de tools.

### 9.3 Iteracion 1: tool execution
- Ejecuta `query_materials_database`.
- `tool_result.status=success`.
- `apply_tool_result(...)` actualiza `state.hypotheses` y `state.properties_collected`.

### 9.4 Evaluacion 1 (mode=evaluate)
Respuesta evaluator:

```json
{
   "stop": false,
   "constraints_ok": false,
   "modify_plan": true,
   "feedback": "falta validar restricciones del usuario"
}
```

Accion en loop:
- No stop (constraints no satisfechas).
- Como `modify_plan=true` y `replans_used<2`, se ejecuta replan.

### 9.5 Replan
Planner recibe:
- `history` operativo filtrado,
- `state` minimo (`cursor`, `replans_used`),
- `execution_state.feedback` con texto del evaluator.

Genera plan actualizado; `state.plan` se reemplaza y `replans_used += 1`.

### 9.6 Iteracion 2: tool execution
- Ejecuta `validate_material_constraints`.
- `apply_tool_result(...)` escribe `state.constraints["constraint_validation"]`.

### 9.7 Evaluacion 2 y stop
Respuesta evaluator:

```json
{
   "stop": true,
   "constraints_ok": true,
   "modify_plan": false,
   "feedback": "evidencia suficiente"
}
```

Accion final:
- `state.stop_reason = "sufficient_evidence"`
- `state.plan.status = "completed"`
- termina loop.

## 10. Referencia de stop reasons actuales
Valores observables en runtime v4:
- `sufficient_evidence`
- `budget_exhausted`
- `plan_exhausted`
- `precondition_failed`
- `tool_execution_failed`
- `evaluator_failed`
- `planner_failed`

**Ultima actualizacion:** Abril 7, 2026
**Version documento:** v4.1
**Tipo:** Tecnico operativo