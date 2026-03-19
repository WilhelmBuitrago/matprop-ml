# Servicio Agent Policy (Ollama)

## 1. Nombre del servicio
Agent Policy (Ollama)

## 2. Descripcion
Servicio FastAPI que funciona como politica y planificador de herramientas. Orquesta modelos Ollama para planificacion (tool calls) y completions conversacionales, valida esquemas JSON y expone endpoints HTTP para planeacion y metadatos.

## 3. Responsabilidad dentro del sistema
- Generar planes de ejecucion (tool calls) a partir de prompts.
- Ejecutar completions de chat via Ollama.
- Publicar informacion de politica y healthcheck.

## 4. Dependencias
### 4.1 Internas
- Agent Core en `http://agent-core:8004` para health y catalogo de tools.

### 4.2 Externas
- Ollama (daemon local) y libreria `ollama`.
- FastAPI, Pydantic, JSONSchema, Requests, NumPy.

## 5. Requisitos del entorno
- Runtime: Python 3 (instalado en imagen `ollama/ollama`).
- Variables de entorno:
  - `AGENTS_OLLAMA_KEEP_ALIVE` (opcional, default `0s`): controla el `keep_alive` aplicado a cada `ollama.chat`.
  - `AGENTS_OLLAMA_PREFER_GPU` (opcional, default `true`): indica preferencia de uso GPU; si no se detecta GPU, el servicio cae a CPU.
  - `NVIDIA_VISIBLE_DEVICES` (opcional, orquestador): usada para deteccion de GPU en contenedor.
- Puerto expuesto: 8003.
- Requisitos de hardware: GPU recomendada para descargas y serving.
- Requisitos de red: acceso HTTP a `agent-core`.

## 6. Estructura de carpetas (vision general)
- `src/api/`: capa HTTP y routing.
- `requirements.txt`: dependencias Python.
- `Dockerfile`: imagen basada en Ollama con uvicorn.

## 7. Descripcion detallada de archivos

### 7.1 Dockerfile
- Rol del archivo: inicializa Ollama, instala Python y ejecuta `uvicorn`.
- Funciones publicas: No aplica.

### 7.2 requirements.txt
- Rol del archivo: dependencias de la API y validacion.
- Funciones publicas: No aplica.

### 7.3 src/api/app.py
- Rol del archivo: crea FastAPI con lifespan y router.
- Funciones publicas: No aplica.

### 7.4 src/api/router.py
- Rol del archivo: router raiz y montaje de v1.
- Funciones publicas: No aplica.

### 7.5 src/api/v1/router.py
- Rol del archivo: endpoints v1 y ciclo de vida.
- Funciones publicas:
  - Firma: `lifespan(app: FastAPI) -> AsyncIterator[None]`
    - Inputs: `app` instancia FastAPI.
    - Outputs: inicializa servicios globales.
    - Efectos secundarios: descarga modelos y crea singletons.
    - Excepciones: propagadas por servicios Ollama.
    - Restricciones: requiere acceso a Ollama.
  - Firma: `get_intentions(request: IntentionRequest) -> ExecutionPlan`
    - Inputs: modelo, prompt, max_tokens.
    - Outputs: plan de pasos (`steps`).
    - Efectos secundarios: llamadas a `agent-core` y a Ollama.
    - Excepciones: `PolicyOutputError` y `RuntimeError`.
    - Restricciones: requiere catalogo de tools valido.
  - Firma: `get_completions(request: CompletionRequest) -> str`
    - Inputs: historial de mensajes, temperatura, max_tokens.
    - Outputs: texto generado por el modelo.
    - Efectos secundarios: llamada a Ollama.
    - Excepciones: `RuntimeError`.
    - Restricciones: requiere modelo instalado.
  - Firma: `get_info() -> dict`
    - Inputs: No aplica.
    - Outputs: metadatos del servicio y planner.
    - Efectos secundarios: No aplica.
    - Excepciones: No aplica.
    - Restricciones: No aplica.
  - Firma: `health_check() -> dict`
    - Inputs: No aplica.
    - Outputs: `{ "status": "ok" }`.
    - Efectos secundarios: No aplica.
    - Excepciones: No aplica.
    - Restricciones: No aplica.

### 7.6 src/api/v1/scheme.py
- Rol del archivo: modelos Pydantic para planificacion y chat.
- Funciones publicas: No aplica.

### 7.7 src/api/v1/service.py
- Rol del archivo: servicios de negocio (carga de modelos, planning, chat, info).
- Funciones publicas:
  - Firma: `resolve_keep_alive() -> str`
    - Inputs: variable de entorno `AGENTS_OLLAMA_KEEP_ALIVE`.
    - Outputs: valor de keep_alive efectivo (string).
    - Efectos secundarios: No aplica.
    - Excepciones: No aplica.
    - Restricciones: fallback a `0s` si vacio o ausente.
  - Firma: `_ollama_chat_with_runtime(model: str, messages: List[Dict[str, Any]], **kwargs)`
    - Inputs: parametros de llamada a Ollama.
    - Outputs: respuesta cruda de `ollama.chat`.
    - Efectos secundarios: serializa ejecucion de inferencia via lock global y emite logs de runtime.
    - Excepciones: propagadas por `ollama.chat`.
    - Restricciones: todas las llamadas a modelo deben pasar por este wrapper para garantizar secuencialidad y keep_alive uniforme.
  - Firma: `LoadModelsService.__init__(self, names: list | None = None) -> None`
    - Inputs: lista opcional de modelos.
    - Outputs: inicializa nombres.
    - Efectos secundarios: No aplica.
    - Excepciones: No aplica.
    - Restricciones: nombres deben existir en Ollama.
  - Firma: `LoadModelsService.download_models(self) -> None`
    - Inputs: No aplica.
    - Outputs: No aplica.
    - Efectos secundarios: llama `ollama.list` y `ollama.pull`.
    - Excepciones: loguea fallos en descargas.
    - Restricciones: requiere acceso a repositorios Ollama.
  - Firma: `ChatService.chat(self, request: CompletionRequest) -> Dict[str, Any]`
    - Inputs: historial, temperatura, max_tokens.
    - Outputs: texto de respuesta.
    - Efectos secundarios: llamada a `ollama.chat`.
    - Excepciones: `RuntimeError`.
    - Restricciones: modelo `self.name` debe existir.
  - Firma: `CifService.get_cif(self, compound_name: str, max_tokens: int = 512) -> str`
    - Inputs: nombre del compuesto.
    - Outputs: contenido CIF.
    - Efectos secundarios: llamada a `ollama.chat`.
    - Excepciones: `RuntimeError`.
    - Restricciones: no expuesto por router v1.
  - Firma: `PlanningService.plan(self, payload: IntentionRequest, attempts: int = 5) -> ExecutionPlan`
    - Inputs: modelo, prompt, max_tokens.
    - Outputs: plan validado de tool calls.
    - Efectos secundarios: llamadas a `agent-core` y Ollama; logs.
    - Excepciones: `PolicyOutputError` y `RuntimeError`.
    - Restricciones: requiere tools validos y schema JSON correcto.
  - Firma: `PlanningService.is_valid(self, instance: dict, schema: dict) -> bool`
    - Inputs: instancia y schema JSON.
    - Outputs: boolean.
    - Efectos secundarios: No aplica.
    - Excepciones: No aplica.
    - Restricciones: No aplica.
  - Firma: `PlanningService._parse_steps(self, steps: List[PlanStep]) -> List[PlanStep]`
    - Inputs: lista de pasos.
    - Outputs: pasos validados y normalizados.
    - Efectos secundarios: llamadas adicionales a Ollama.
    - Excepciones: `PolicyOutputError`.
    - Restricciones: asegura paso final `delegate_to_reasoner`.
  - Firma: `PlanningService.get_info(self) -> dict`
    - Inputs: No aplica.
    - Outputs: metadatos del planner.
    - Efectos secundarios: No aplica.
    - Excepciones: No aplica.
    - Restricciones: `self.name` debe estar inicializado.
  - Firma: `InfoService.get_info(self) -> dict`
    - Inputs: No aplica.
    - Outputs: metadatos del servicio.
    - Efectos secundarios: instancia `PlanningService` temporal.
    - Excepciones: No aplica.
    - Restricciones: No aplica.

## 8. Modelos de datos utilizados
- `CompletionRequest`: `history`, `temperature`, `max_tokens`.
- `IntentionRequest`: `model_name`, `prompt`, `max_tokens`.
- `PlanStep`: `tool`, `arguments`.
- `ExecutionPlan`: `steps`.

## 9. API endpoints (si aplica)
- `POST /v1/intention`: request `IntentionRequest`, response `ExecutionPlan`.
- `POST /v1/completions`: request `CompletionRequest`, response `str`.
- `GET /v1/info`: metadatos del planner y version de politica.
- `GET /v1/health`: `{ "status": "ok" }`.

## 10. Flujo de trabajo
1) Inicializa modelos Ollama en `lifespan`.
2) `/v1/intention` llama a `agent-core` para tools y usa `ollama.chat` con tool calls.
3) Se valida el plan y se fuerza un paso `delegate_to_reasoner`.
4) `/v1/completions` delega a `ChatService`.

## 11. Diagrama textual del flujo (opcional)
Cliente -> Agent Policy (/v1/intention) -> Agent Core (/v1/tools) -> Ollama -> Plan

## 12. Consideraciones tecnicas / decisiones de diseno
- Los modelos a descargar estan hardcodeados en `LoadModelsService`.
- La validacion de argumentos se reintenta hasta 3 veces con compilador JSON.
- `CifService` no esta expuesto via router v1.

## 13. Operacion y despliegue (si aplica)
- Docker inicia `ollama serve` y `uvicorn` en el mismo contenedor.
- Puerto 8003 expuesto.

## 14. Observabilidad y soporte (si aplica)
- Logging basico en servicios de planning/chat.
- Healthcheck en `/v1/health`.

## 15. Actualizacion de arquitectura (2026-03-15)
- Planeacion robusta:
  - Se corrigio la convergencia de validacion de pasos para considerar tambien casos ya validos por schema.
  - Se agrego guard clause para evitar acceso a `parsed_steps[-1]` cuando no hay pasos validos.
  - En casos invalidos se retorna `PolicyOutputError("EMPTY_PLAN")` en lugar de crash por indice.
- Resiliencia interna:
  - Las llamadas HTTP a `agent-core` (`/v1/health`, `/v1/tools`) ahora incluyen `timeout` explicito.
- Compatibilidad de herramientas:
  - El planner consume el catalogo filtrado de herramientas implementadas que publica `agent-core`.

## 16. Integracion con Agent Core v2 (2026-03-18)
- Rol dentro de los modos de chat:
  - En modo simple (frontend OFF -> `agent-core /v1/completions`), este servicio participa como planner via `POST /v1/intention`.
  - En modo agentico (frontend ON -> `agent-core /v2/completions`), `agent-core` ejecuta su loop interno v2 y puede reutilizar estrategia/politica local sin cambiar el contrato publico de este servicio.
- Contrato estable para orquestacion:
  - Se mantiene `POST /v1/intention` como interfaz de planificacion para consumers internos.
  - Se mantiene `POST /v1/completions` como capacidad conversacional de respaldo en la capa de agentes.
- Alcance:
  - Este servicio no expone endpoints `v2` propios; la version `v2` del comportamiento agente vive en `agent_core`.

## 17. Runtime de inferencia secuencial y GPU (2026-03-18)
- Secuencialidad de ejecucion:
  - Todas las llamadas a `ollama.chat` se ejecutan mediante un lock global en `service.py`.
  - Esto evita contencion concurrente de VRAM y estabiliza el comportamiento bajo carga.
- Politica de lifecycle de modelo:
  - `keep_alive` se aplica de forma uniforme a todas las inferencias (chat/planning/compilacion de argumentos/CIF).
  - El valor se controla por `AGENTS_OLLAMA_KEEP_ALIVE` y por defecto queda en `0s`.
- Verificacion de GPU en startup:
  - En el `lifespan` de `router.py` se detecta disponibilidad de GPU (variables NVIDIA y `nvidia-smi`).
  - Se registran logs con `keep_alive`, `gpu_requested` y `gpu_detected`.
  - Si la GPU fue solicitada pero no detectada, se registra warning y el servicio continua en CPU.
- Observabilidad operativa:
  - Logs de runtime para cada inferencia: espera de lock, lock adquirido y lock liberado con latencia (`elapsed_ms`).