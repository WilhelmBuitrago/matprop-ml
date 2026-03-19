# Agent Core - Documentacion tecnica

## 1. Nombre del servicio
Agent Core API

## 2. Descripcion
Servicio FastAPI que orquesta herramientas de consulta de materiales y delega la generacion final de respuestas a un backend conversacional. Recibe prompts, planifica herramientas via un servicio de politica, ejecuta herramientas locales y construye un contexto para el chat.

## 3. Responsabilidad dentro del sistema
- Actuar como pasarela entre el planificador (agents) y el backend de chat.
- Ejecutar herramientas locales de busqueda y propiedades de materiales.
- Exponer endpoints de completions y herramientas disponibles.

## 4. Dependencias
### 4.1 Internas
- Servicio `agents` (planner) en `http://agents:8003/v1/intention`.
- Servicio `backend-llm` (chat) en `http://backend-llm:8001/v1/chat`.

### 4.2 Externas
- FastAPI, Starlette CORS, Pydantic, Requests.
- `mp_api` y `pymatgen` para consultas a Materials Project.

## 5. Requisitos del entorno
- Runtime: Python 3.11 (imagen `python:3.11-slim`).
- Variables de entorno: No aplica (clave de Materials Project esta hardcodeada en `tools.py`).
- Puerto expuesto: 8004.
- Requisitos de hardware: No aplica.
- Requisitos de red: acceso HTTP a `agents` y `backend-llm`; acceso a Materials Project.

## 6. Estructura de carpetas (vision general)
- `src/api/`: capa HTTP y routing.
- `src/tools/`: herramientas y esquemas JSON de tool-calling.
- `requirements.txt`: dependencias Python.
- `Dockerfile`: definicion del contenedor.

## 7. Descripcion detallada de archivos

### 7.1 src/api/app.py
- Rol del archivo: inicializa FastAPI, CORS y router principal.
- Funciones publicas: No aplica.

### 7.2 src/api/router.py
- Rol del archivo: router raiz y montaje de v1.
- Funciones publicas: No aplica.

### 7.3 src/api/v1/router.py
- Rol del archivo: endpoints HTTP v1 y ciclo de vida.
- Funciones publicas:
  - Firma: `lifespan(app: FastAPI) -> AsyncIterator[None]`
    - Inputs: `app` instancia FastAPI.
    - Outputs: contexto de vida para inicializar `CompletionService`.
    - Efectos secundarios: crea singleton global `chat_service`.
    - Excepciones: No aplica.
    - Restricciones: depende de inicializacion global.
  - Firma: `get_tools() -> Tools`
    - Inputs: No aplica.
    - Outputs: lista de herramientas (`AVAILABLES_TOOLS`).
    - Efectos secundarios: No aplica.
    - Excepciones: No aplica.
    - Restricciones: No aplica.
  - Firma: `chat(request: CompletionRequest) -> CompletionResponse`
    - Inputs: `request` con prompt y limites de tokens.
    - Outputs: respuesta con `choices` y `usage`.
    - Efectos secundarios: llamadas HTTP a planner y backend-llm.
    - Excepciones: `RuntimeError` ante fallos de planner/chat.
    - Restricciones: requiere `chat_service` inicializado.
  - Firma: `historial_summary_endpoint() -> dict`
    - Inputs: No aplica.
    - Outputs: JSON del backend-llm.
    - Efectos secundarios: llamada HTTP a `http://localhost:8001/v1/historial_summary`.
    - Excepciones: propagadas por `requests`.
    - Restricciones: usa `localhost` en lugar de nombre de servicio.
  - Firma: `clear_history_endpoint() -> dict`
    - Inputs: No aplica.
    - Outputs: JSON del backend-llm.
    - Efectos secundarios: llamada HTTP a `http://localhost:8001/v1/clear_history`.
    - Excepciones: propagadas por `requests`.
    - Restricciones: usa `localhost` en lugar de nombre de servicio.
  - Firma: `conversation_history_endpoint() -> dict`
    - Inputs: No aplica.
    - Outputs: JSON del backend-llm.
    - Efectos secundarios: llamada HTTP a `http://localhost:8001/v1/conversation_history`.
    - Excepciones: propagadas por `requests`.
    - Restricciones: usa `localhost` en lugar de nombre de servicio.
  - Firma: `health_check() -> dict`
    - Inputs: No aplica.
    - Outputs: `{ "status": "ok" }`.
    - Efectos secundarios: No aplica.
    - Excepciones: No aplica.
    - Restricciones: No aplica.

### 7.4 src/api/v1/scheme.py
- Rol del archivo: modelos Pydantic de request/response.
- Funciones publicas: No aplica.

### 7.5 src/api/v1/service.py
- Rol del archivo: orquestador principal de completions.
- Funciones publicas:
  - Firma: `CompletionService.__init__(self) -> None`
    - Inputs: No aplica.
    - Outputs: inicializa URLs y herramientas.
    - Efectos secundarios: No aplica.
    - Excepciones: No aplica.
    - Restricciones: endpoints internos hardcodeados.
  - Firma: `CompletionService.chat(self, request: CompletionRequest) -> CompletionResponse`
    - Inputs: `request.prompt`, `request.max_tokens_for_context`.
    - Outputs: `CompletionResponse` con `choices` y `usage`.
    - Efectos secundarios: llamadas HTTP a planner y backend-llm; logs.
    - Excepciones: `RuntimeError` en fallos de red o parsing.
    - Restricciones: ignora `temperature` y `max_tokens_for_response` (comentados).
  - Firma: `CompletionService.approximate_tokens(self, text: str) -> int`
    - Inputs: texto.
    - Outputs: tokens aproximados.
    - Efectos secundarios: No aplica.
    - Excepciones: No aplica.
    - Restricciones: aproximacion simple (1 token ~ 4 chars).

### 7.6 src/tools/config.py
- Rol del archivo: catalogo JSON de herramientas disponibles.
- Funciones publicas: No aplica.

### 7.7 src/tools/tools.py
- Rol del archivo: herramientas de materiales y normalizacion.
- Funciones publicas:
  - Firma: `normalize_filters(filters: dict) -> dict`
    - Inputs: filtros de busqueda con rangos y flags.
    - Outputs: kwargs validados para `MPRester`.
    - Efectos secundarios: No aplica.
    - Excepciones: `ValueError` por formatos invalidos.
    - Restricciones: solo claves en `ALLOWED_FILTERS`.
  - Firma: `normalize_material_query(material) -> dict`
    - Inputs: int, str o list (IDs, formula o chemsys).
    - Outputs: dict con tipo y valores normalizados.
    - Efectos secundarios: No aplica.
    - Excepciones: `ValueError` por tipos mixtos o formato invalido.
    - Restricciones: valida con regex y no permite mezclar tipos.
  - Firma: `SearchMaterialsTool.search_materials(self, query: Dict) -> List[Dict]`
    - Inputs: `query.material` y `query.filters`.
    - Outputs: lista de resumenes de materiales.
    - Efectos secundarios: llamadas a Materials Project via `MPRester`.
    - Excepciones: errores de validacion o API.
    - Restricciones: requiere API key valida.
  - Firma: `SearchMaterialsTool.execute(self, **kwargs) -> List[Dict]`
    - Inputs: `query` en kwargs.
    - Outputs: lista de materiales.
    - Efectos secundarios: iguales a `search_materials`.
    - Excepciones: iguales a `search_materials`.
    - Restricciones: No aplica.
  - Firma: `GetMaterialPropertiesTool.get_material_properties(self, query: Dict, propertys: List) -> Dict`
    - Inputs: `query` de material, `propertys` lista de campos.
    - Outputs: dict con grupos `identity`, `termodynamic`, `crystallography`, `electronic`.
    - Efectos secundarios: llamadas a Materials Project via `SearchMaterialsTool`.
    - Excepciones: errores de validacion o API.
    - Restricciones: el parametro se llama `propertys` (no `properties`).
  - Firma: `GetMaterialPropertiesTool.execute(self, **kwargs) -> Dict`
    - Inputs: `query`, `propertys` en kwargs.
    - Outputs: resumen de propiedades o error.
    - Efectos secundarios: iguales a `get_material_properties`.
    - Excepciones: iguales a `get_material_properties`.
    - Restricciones: No aplica.
  - Firma: `visualize_material_structure(material: Union[str, Structure]) -> str`
    - Inputs: ID de material o `pymatgen.Structure`.
    - Outputs: objeto visualizador (ChemView) serializable.
    - Efectos secundarios: llamadas a Materials Project si se pasa ID.
    - Excepciones: `ValueError` si el tipo no es valido.
    - Restricciones: requiere `pymatgen` y API key valida.

## 8. Modelos de datos utilizados
- `Tools`: `{ tools: List[Dict[str, Any]] }`.
- `CompletionRequest`: `prompt`, `temperature`, `max_tokens_for_response`, `max_tokens_for_context`.
- `CompletionResponse`: `id`, `object`, `choices`, `usage`.
- Esquemas JSON de `AVAILABLES_TOOLS` para tool-calling.

## 9. API endpoints (si aplica)
- `GET /v1/tools`: respuesta `Tools`.
- `POST /v1/completions`: request `CompletionRequest`, response `CompletionResponse`.
- `GET /v1/historial_summary`: proxy a backend-llm.
- `GET /v1/clear_history`: proxy a backend-llm.
- `GET /v1/conversation_history`: proxy a backend-llm.
- `GET /v1/health`: `{ "status": "ok" }`.

## 10. Flujo de trabajo
1) Recibe `prompt` en `/v1/completions`.
2) Solicita plan al servicio `agents`.
3) Ejecuta herramientas locales segun plan.
4) Construye contexto y llama a `backend-llm`.
5) Devuelve respuesta con `usage` aproximado.

## 11. Diagrama textual del flujo (opcional)
Cliente -> Agent Core (/v1/completions) -> Agents (/v1/intention) -> Tools -> Backend-LLM (/v1/chat) -> Respuesta

## 12. Consideraciones tecnicas / decisiones de diseno
- CORS abierto para simplicidad de integracion.
- Tokens aproximados por longitud de texto.
- `historial_summary` y similares usan `localhost` (no nombre de servicio).
- API key de Materials Project hardcodeada en `tools.py`.

## 13. Operacion y despliegue (si aplica)
- Docker: expone 8004 y ejecuta `uvicorn api.app:app`.
- Requiere que `agents` y `backend-llm` esten disponibles en red.

## 14. Observabilidad y soporte (si aplica)
- Logging basico en `CompletionService`.
- Healthcheck en `/v1/health`.

## 15. Actualizacion de arquitectura (2026-03-15)
- Secretos y entorno:
  - Se elimino el hardcode de clave para Materials Project.
  - Se requiere `MP_API_KEY` al arranque; si falta, el servicio falla de forma explicita.
  - Nuevas variables soportadas: `BACKEND_LLM_URL`, `INTERNAL_HTTP_TIMEOUT_SECONDS`, `CORS_ALLOW_ORIGINS`.
- Catalogo de herramientas:
  - `config.py` mantiene el schema completo, pero `/v1/tools` ahora expone solo herramientas implementadas en runtime (`search_materials`, `get_material_properties`, `delegate_to_reasoner`).
  - Se corrigio schema JSON invalido (`type:` -> `type`) y se alineo `filters` como opcional en `search_materials`.
- Resiliencia HTTP interna:
  - Se agregaron `timeout`, reintentos con backoff y manejo mas robusto de errores para llamadas a `agents` y `backend-llm`.
  - Se eliminaron endpoints hardcodeados con `localhost` para trafico interno en contenedores.
- API de historial:
  - Se agrego `POST /v1/clear_history` como metodo principal.
  - Se mantiene `GET /v1/clear_history` temporalmente como deprecated (1 release).
- Seguridad CORS:
  - Se reemplazo `allow_origins=["*"]` por whitelist configurable.
  - `allow_credentials` se desactiva automaticamente si existe wildcard.

## 16. API v2 y modo agentico completo (2026-03-18)

### 16.1 Objetivo de v2
- `v1` mantiene un flujo lineal (plan -> tools -> reasoner).
- `v2` agrega un loop agentico con estado, evaluacion de evidencia, politicas de accion y presupuestos de ejecucion.
- El endpoint expuesto es `POST /v2/completions`.

### 16.2 Contrato HTTP v2
- Endpoint: `POST /v2/completions`.
- Request (`CompletionRequestV2`):
  - `prompt: str`
  - `temperature: float = 0.2`
  - `max_tokens_for_response: int = 512`
  - `max_tokens_for_context: int = 1024`
  - `max_iterations: int = 6`
  - `max_tool_calls: int = 6`
  - `max_wall_time_ms: int = 20000`
  - `max_reclassifications: int = 1`
  - `max_think_steps: int = 1`
- Response (`CompletionResponseV2`):
  - `id`, `object`, `choices`, `usage` (compatible con v1)
  - `metadata` (solo v2):
    - `trace_id`
    - `iterations_count`
    - `tool_calls_count`
    - `reclassifications_count`
    - `think_steps_count`
    - `context_tokens_used`
    - `stop_reason`
    - `elapsed_ms`

### 16.3 Componentes internos de v2
- `src/api/v2/state.py`
  - Tipos de accion (`ActionType`): `CALL_TOOL`, `RETRY_TOOL`, `REFINE_QUERY`, `RECLASSIFY_INTENT`, `THINK`, `DELEGATE_TO_REASONER`, `FINALIZE_SUCCESS`, `FINALIZE_FAILURE`.
  - Clases de evaluacion (`EvalClass`): `SUFFICIENT`, `INSUFFICIENT`, `RECOVERABLE_ERROR`, `TERMINAL_ERROR`.
  - Estado acumulado del agente: `AgentState`, `BudgetState`, `Observation`, `EvaluationResult`, `DecisionRecord`.
- `src/api/v2/policy.py`
  - Clasificacion de intencion (`material_lookup`, `property_lookup`, `explanation_only`, `unknown`).
  - Mascaras de accion por intencion (`INTENT_ACTION_MASK`).
  - Priorizacion de herramientas (`INTENT_TOOL_PRIORITY`).
  - Umbrales de paro por evidencia (`INTENT_STOP_POLICY`).
  - Seleccion determinista de siguiente accion (`choose_next_action`).
- `src/api/v2/evaluator.py`
  - Evalua observaciones por herramienta y por coherencia con query.
  - Emite clasificacion de suficiencia o error recuperable/terminal.
  - Reglas especificas para `search_materials` y `get_material_properties`.
- `src/api/v2/context_builder.py`
  - Construye contexto final para reasoner con compresion de payload cuando excede presupuesto de tokens.
  - Prioriza observaciones recientes, validas y no vacias.
- `src/api/v2/tool_layer.py`
  - Capa de ejecucion de herramientas con timeout y normalizacion de resultado.
  - Clasifica errores en `TOOL_NOT_FOUND`, `TOOL_NOT_EXECUTABLE`, `TOOL_TIMEOUT`, `TOOL_INPUT_ERROR`, `TOOL_UPSTREAM_ERROR`.
- `src/api/v2/service.py`
  - Orquestador principal del loop agentico.
  - Mantiene contador de iteraciones, tool calls y presupuestos.
  - Genera respuesta final mediante `backend-llm` y persiste trazas.

### 16.4 Flujo simplificado de v2
1) Se clasifica la intencion inicial y se inicializa `AgentState`.
2) La policy elige accion segun estado, presupuesto y ultima evaluacion.
3) Si la accion requiere herramienta, `ToolExecutionLayer` ejecuta y devuelve `ToolResult`.
4) `Evaluator` clasifica la observacion en suficiente/insuficiente/error.
5) `ContextBuilder` arma contexto comprimido para preservar budget.
6) Se aplican hard stops (`max_wall_time_ms`, `max_iterations`, `max_tool_calls`, `max_context_tokens`).
7) El agente delega al reasoner (`/v1/chat` de backend-llm) para redaccion final.

### 16.5 Compatibilidad con frontend More context
- Modo OFF en frontend (`More context` desactivado):
  - Llamada a `POST /v1/completions`.
  - Flujo chat simple de una sola pasada.
- Modo ON en frontend (`More context` activado):
  - Llamada a `POST /v2/completions`.
  - Flujo agentico completo con metadatos de ejecucion.
- Compatibilidad de respuesta:
  - Tanto `v1` como `v2` devuelven `choices[0].text`, por lo que el cliente puede conmutar endpoints sin cambiar el render base del mensaje.

### 16.6 Endpoints vigentes
- `GET /v1/tools`
- `POST /v1/completions`
- `POST /v2/completions`
- `GET /v1/historial_summary`
- `POST /v1/clear_history`
- `GET /v1/clear_history` (deprecated)
- `GET /v1/conversation_history`
- `GET /v1/health`
