# Agents - Documentacion Tecnica Determinista (Runtime v2)

## 1. Alcance y fuente de verdad
Este documento describe el comportamiento implementado actualmente en el servicio `agents` (v2), sin proponer features nuevas.

Fuente de verdad usada:
- `src/api/app.py`
- `src/api/router.py`
- `src/api/v2/router.py`
- `src/api/v2/scheme.py`
- `src/api/v2/service.py`
- `src/api/v2/models.py`
- `src/models/registry.py`
- `src/services/ollama_client.py`
- `src/services/generation_service.py`
- `src/services/model_service.py`
- `src/services/crystal_spec_extraction_agent.py`

Superficie publica vigente:
- `POST /v2/completions`
- `POST /v2/decision`
- `POST /v2/planning-evaluator`
- `POST /v2/insights`
- `POST /v2/embeddings`
- `POST /v2/cif`
- `POST /v2/crystal/spec`
- `POST /v2/crystal/complete`
- `GET /v2/info`
- `GET /v2/health`

## 2. Arquitectura operativa

### 2.1 Vista de capas
Capas implementadas:
1. Capa HTTP (`src/api/v2/router.py`): valida request y mapea errores a HTTP.
2. Capa de servicios (`src/api/v2/service.py`): orquesta dependencias y wrappers por capacidad.
3. Capa de modelos estructurados (`src/api/v2/models.py`): prompt, parseo JSON y validacion Pydantic para flujos que requieren salida estructurada.
4. Capa runtime Ollama (`src/services/ollama_client.py`): operaciones `chat`, `embeddings`, `list`, `pull`.
5. Capa de configuracion (`src/models/registry.py`): ownership de resolucion de modelos via entorno.

### 2.2 Ensamblado en runtime
`V2RuntimeServices` instancia con un `OllamaClient` compartido:
- `loader`: `LoadModelsService`
- `chat`: `ChatService`
- `cif`: `CifService`
- `crystal_spec`: `CrystalSpecExtractionAgent`
- `embeddings`: `EmbeddingsService`
- `decision`: `DecisionService`
- `planning_evaluator`: `PlanningEvaluatorService`
- `insights`: `InsightsService`
- `info`: `InfoService`

Propiedad relevante: se minimiza acoplamiento de endpoints con lógica de prompting y con llamadas low-level a Ollama.

## 3. Lifespan, startup y disponibilidad

### 3.1 Inicializacion
En el lifespan de `v2`:
1. Resuelve `keep_alive` desde `AGENTS_OLLAMA_KEEP_ALIVE` (default `0s`).
2. Evalua preferencia GPU (`AGENTS_OLLAMA_PREFER_GPU`).
3. Detecta GPU por `NVIDIA_VISIBLE_DEVICES` o `nvidia-smi -L`.
4. Crea `V2RuntimeServices`.
5. Ejecuta `download_models()`.

### 3.2 Efecto de inicializacion incompleta
Si `runtime_services` es `None`, endpoints de inferencia responden:
- `HTTP 503` con `runtime_services_unavailable`.

## 4. Contratos HTTP (Pydantic) y validaciones

### 4.1 Esquemas de entrada/salida
Definidos en `src/api/v2/scheme.py`.

Contratos principales:
- `CompletionRequest`
- `DecisionModelInput` / `DecisionModelOutput`
- `PlanningEvaluatorRequest` / `PlanningEvaluatorOutput`
- `InsightRequest` / `InsightResponse`
- `CifRequest`
- `CrystalSpecExtractionRequest`
- `CrystalCompletionRequest`
- `EmbeddingRequest` / `EmbeddingResponse` (en router)

### 4.2 Restricciones formales destacadas
- `PlanningEvaluatorRequest.mode`: solo `plan | evaluate`.
- `PlanningEvaluatorRequest.max_steps`: `1..8`.
- `PlanningEvaluatorOutput.steps`: maximo 8.
- `EmbeddingRequest.texts`: minimo 1 item.
- `PlanningStep.action`: `use_tool | respond`.
- `PlanningStep` exige `tool` cuando `action=use_tool`.

### 4.3 Politica de campos extra
En esquemas críticos de planning/evaluator se usa `ConfigDict(extra="forbid")`, por lo que campos no esperados en esos modelos generan error de validacion.

## 5. Especificacion funcional por endpoint

### 5.1 POST /v2/completions
Objetivo: generación textual general.

Pipeline:
1. Router valida `CompletionRequest`.
2. `ChatService.chat(...)` construye opciones (`temperature`, `num_predict`, `stop` opcional).
3. `OllamaClient.chat(...)` invoca Ollama.
4. Retorna `message.content` como string.

Errores mapeados:
- `503 chat_failed: ...`

### 5.2 POST /v2/decision
Objetivo: producir una decision estructurada de control de agente.

Pipeline:
1. `DecisionModel` construye prompt con acciones permitidas y tool schema.
2. Ejecuta `chat` con temperatura 0.3.
3. Extrae JSON estricto (`_extract_json_dict`).
4. Valida contra `DecisionModelOutput`.

Errores mapeados:
- `503 decision_model_failed: ...`

### 5.3 POST /v2/planning-evaluator
Objetivo: unificar planeacion y evaluacion en un solo contrato.

Modo `plan`:
- prompt de planner con `query`, `state`, `tools_available`, `max_steps`.
- salida esperada: `steps`.
- normalizacion de pasos en `_normalize_steps(...)`:
  - filtra tools no permitidos,
  - fuerza shape de `PlanningStep`,
  - agrega `respond` final cuando corresponde,
  - fallback defensivo si no hay pasos validos.

Modo `evaluate`:
- prompt de evaluator con `query`, `history`, `plan`, `state`, `execution_state`.
- salida esperada: `stop`, `constraints_ok`, `modify_plan`, `feedback`.
- fallback defensivo: `constraints_ok = bool(constraints_ok or stop)` cuando no viene explícito.

Errores mapeados:
- `503 planning_evaluator_failed: ...`

### 5.4 POST /v2/insights
Objetivo: extraer hechos técnicos de un chunk textual.

Pipeline:
1. Prompt exige "JSON array of strings".
2. Parseo tolerante con `_safe_json(...)`.
3. Si devuelve lista, limpia strings vacíos.
4. Si devuelve objeto, intenta `extracted_info` o `facts`.

Errores mapeados:
- `503 insights_failed: ...`

### 5.5 POST /v2/embeddings
Objetivo: generar embeddings por lote.

Pipeline:
1. valida `texts` no vacía.
2. `EmbeddingsService.embed_texts` llama `embed_batch`.
3. `embed_batch` itera secuencialmente sobre `embed`.
4. verifica correspondencia de cardinalidad entre entradas y embeddings.

Errores mapeados:
- `400` si lista vacía.
- `500 Embedding service failed: ...` en `RuntimeError`.
- `500 Internal server error` en error inesperado.

### 5.6 POST /v2/cif
Objetivo: obtener contenido CIF para un compuesto.

Pipeline:
1. construye prompt fijo para pedir solo contenido CIF.
2. ejecuta chat con temperatura 0.0.
3. retorna string sin post-procesamiento sintáctico CIF.

Errores mapeados:
- `503 cif_failed: ...`

### 5.7 POST /v2/crystal/spec
Objetivo: completar campos de spec cristalográfica a partir de texto libre y spec determinista previa.

Pipeline:
1. `CrystalSpecExtractionAgent.extract(...)` arma prompt con `query` + `deterministic_spec`.
2. sistema exige JSON con llaves concretas.
3. parseo seguro en `_safe_json`.
4. retorna `{"spec": parsed}`.

Errores mapeados:
- `503 crystal_spec_failed: ...`

### 5.8 POST /v2/crystal/complete
Objetivo: generación libre (controlada por prompt) para tareas cristalográficas.

Pipeline:
1. usa `system_message` y `user_prompt` tal como llegan.
2. configura `temperature`, `num_predict`, `stop` opcional.
3. retorna `raw_generation`.

Errores mapeados:
- `503 crystal_complete_failed: ...`

### 5.9 GET /v2/info
Objetivo: metadatos del runtime.

Retorna:
- `service`
- `ChatService.Model`
- `ChatService.Version`
- `policy_version`

### 5.10 GET /v2/health
Objetivo: probe de salud básico.

Retorna:
- `{ "status": "ok" }`

## 6. Seleccion de modelos y ownership

### 6.1 Registro central
`src/models/registry.py` concentra defaults y fallback.

Variables relevantes:
- `AGENT_BASE_MODEL`
- `AGENT_PLANNING_EVALUATOR_MODEL`
- `AGENT_EVALUATOR_MODEL`
- `AGENT_PLANNER_MODEL`
- `AGENT_INSIGHTS_MODEL`
- `AGENT_FINAL_MODEL`
- `AGENT_CIF_MODEL`
- `AGENT_EMBEDDING_MODEL`

Estructuras derivadas:
- `GENERATION_MODELS = {evaluator, final, cif}`
- `ALL_MODELS` (set ordenado para descarga en startup)

### 6.2 Regla de ownership
La seleccion efectiva de modelos para contratos `v2` reside en `agents`, no en el consumidor externo.

## 7. Formatos internos y parseo robusto

### 7.1 Extraccion de JSON estricto
`_extract_json_dict`:
- admite salida fenced JSON,
- busca primer `{` y ultimo `}`,
- exige objeto JSON final.

Impacto: reduce riesgo de aceptar prosa no estructurada en endpoints de control.

### 7.2 Parseo tolerante para insights
`_safe_json` intenta:
1. parseo directo,
2. regex de lista,
3. regex de objeto,
4. fallback `[]`.

Impacto: mejora robustez ante drift de formato en salida LLM.

## 8. Flujo de datos de extremo a extremo (resumen)
1. Cliente HTTP llama endpoint `v2`.
2. Router valida esquema.
3. Servicio correspondiente selecciona modelo (por registry/env).
4. `OllamaClient` ejecuta inferencia o embeddings.
5. Se normaliza/parsa salida cuando aplica.
6. Router devuelve payload o error HTTP.

## 9. Failure modes actuales

### 9.1 Fallos de infraestructura
- Ollama no disponible o timeout interno en SDK.
- modelo no instalado y falla `pull_model`.
- startup parcial con `runtime_services` no inicializado.

### 9.2 Fallos de salida de modelo
- JSON inválido en `decision`/`planning-evaluator`.
- formato ambiguo en `insights` (degrada a lista vacía).
- salida CIF no validada semánticamente.

### 9.3 Fallos de configuración
- variables de entorno vacías o inconsistentes.
- elección de modelos no alineada con capacidad del hardware.

## 10. Restricciones y límites explícitos
- API pública limitada a `v2`.
- `planning-evaluator` acota `max_steps` a 8.
- `embeddings` procesa secuencialmente (sin paralelización interna).
- no existe timeout global por endpoint implementado en código de router/servicio.
- servicio responde request/response; no expone SSE para generación.

## 11. Inconsistencias observables y notas de mantenimiento
Contradicción verificable:
- `src/models/registry.py` no define `AGENTS_DECISION_MODEL`.
- el `Dockerfile` usa `ollama pull ${AGENTS_DECISION_MODEL:-yasserrmd/Qwen2.5-7B-Instruct-1M}` en `CMD`.

Implicación:
- el modelo precargado por `CMD` puede no coincidir con los modelos realmente usados por runtime (`ALL_MODELS`).

Recomendación técnica:
- unificar estrategia de preload del `Dockerfile` con el registry del runtime para evitar pulls redundantes o desalineados.

## 12. Ejemplos mínimos de uso

### 12.1 Planning (modo plan)
```json
POST /v2/planning-evaluator
{
  "mode": "plan",
  "query": "Buscar semiconductor estable con band gap cerca de 1 eV",
  "tools_available": [{"name": "query_materials_database", "description": "..."}],
  "state": {},
  "history": [],
  "plan": {},
  "execution_state": {},
  "max_steps": 4
}
```

Respuesta esperada (shape):
```json
{
  "steps": [
    {
      "action": "use_tool",
      "tool": "query_materials_database",
      "input": {},
      "purpose": "..."
    },
    {
      "action": "respond",
      "purpose": "Respond with available evidence"
    }
  ],
  "stop": null,
  "constraints_ok": null,
  "modify_plan": null,
  "feedback": ""
}
```

### 12.2 Evaluación (modo evaluate)
```json
POST /v2/planning-evaluator
{
  "mode": "evaluate",
  "query": "Buscar semiconductor estable con band gap cerca de 1 eV",
  "history": [],
  "tools_available": [],
  "state": {"materials_count": 1},
  "plan": {"steps": []},
  "execution_state": {"iterations_used": 1},
  "max_steps": 4
}
```

Respuesta esperada (shape):
```json
{
  "steps": [],
  "stop": false,
  "constraints_ok": false,
  "modify_plan": false,
  "feedback": "continue_with_current_plan"
}
```

## 13. Version del documento
- Ultima actualización: Abril 8, 2026
- Version documento: v2.1
- Tipo: técnico operativo
