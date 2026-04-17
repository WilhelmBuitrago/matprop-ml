# Agents Runtime API (v2)

## 1. Que es este servicio
`agents` es el servicio que centraliza el uso de modelos LLM y embeddings sobre Ollama para el ecosistema `matprop-ml`.

En términos simples:
- recibe solicitudes HTTP,
- selecciona el modelo apropiado,
- ejecuta inferencia local,
- devuelve respuestas estructuradas para otros servicios.

El contrato público vigente es `v2`.

## 2. Para que sirve
Este servicio resuelve tareas de IA que otros componentes necesitan, principalmente `agent_core`.

Capacidades disponibles:
- completions generales,
- planning/evaluator para control de ciclo,
- domain critic dedicado para validacion fisica/coherencia,
- extracción de insights desde texto técnico,
- embeddings,
- generación y completado de contenido cristalográfico (CIF/spec),
- endpoints operativos (`info`, `health`).

## 3. Como se integra en matprop-ml
`agents` actúa como runtime de inferencia local.

Rol dentro de la arquitectura:
- ownership de la selección de modelos por variables de entorno,
- acceso unificado a Ollama por `OllamaClient`,
- carga de modelos requeridos al iniciar,
- exposición de endpoints estables consumidos por `agent_core`.

## 4. Arquitectura general
Base tecnológica:
- FastAPI
- SDK `ollama` en Python
- Pydantic v2 para contratos de entrada/salida

Estructura principal:
- `src/api/app.py`: crea la app FastAPI.
- `src/api/router.py`: enruta a `v2`.
- `src/api/v2/router.py`: define endpoints públicos.
- `src/api/v2/scheme.py`: esquemas de request/response.
- `src/api/v2/service.py`: ensambla servicios runtime en `V2RuntimeServices`.
- `src/api/v2/models.py`: prompting + parseo/normalización para modelos estructurados.
- `src/services/ollama_client.py`: acceso común a chat, embeddings, list y pull.
- `src/services/model_service.py`: descarga/verificación de modelos.
- `src/models/registry.py`: resolución de modelos por entorno.

## 5. Endpoints principales (v2)

### `POST /v2/completions`
Genera texto conversacional con el modelo final.

### `POST /v2/planning-evaluator`
Endpoint unificado para:
- `mode="plan"`: crear plan de pasos.
- `mode="evaluate"`: evaluar si detener, continuar o replanificar.

### `POST /v2/domain-critic`
Endpoint dedicado para validacion de dominio fisico sobre un borrador de respuesta.

Entrada esperada:
- `user_query`
- `tool_results`
- `reasoning_steps`
- `draft_response`

Salida:
- texto plano estructurado (`VALID`, `CONFIDENCE`, `ISSUES`) para ser parseado por `agent_core`.

### `POST /v2/decision`
Devuelve una decisión estructurada (`action`, `tool_name`, `tool_arguments`, etc.).

### `POST /v2/insights`
Extrae hechos técnicos relevantes desde un fragmento de texto.

### `POST /v2/embeddings`
Obtiene vectores de embeddings para una lista de textos.

### `POST /v2/cif`
Solicita contenido CIF para un compuesto.

### `POST /v2/crystal/spec`
Completa campos de especificación cristalográfica a partir de consulta + spec determinista.

### `POST /v2/crystal/complete`
Generación libre orientada a cristalografía con `system_message` y `user_prompt`.

### `GET /v2/info`
Devuelve metadatos del runtime.

### `GET /v2/health`
Healthcheck (`{"status":"ok"}`).

## 6. Seleccion de modelos
La selección de modelos se concentra en `src/models/registry.py` vía variables de entorno.

Variables clave:
- `AGENT_BASE_MODEL`
- `AGENT_PLANNING_EVALUATOR_MODEL`
- `AGENT_EVALUATOR_MODEL`
- `AGENT_INSIGHTS_MODEL`
- `AGENT_PLANNER_MODEL`
- `AGENT_FINAL_MODEL`
- `AGENT_CIF_MODEL`
- `AGENT_EMBEDDING_MODEL`
- `AGENT_DOMAIN_CRITIC_MODEL`

Resumen operativo:
- `planning-evaluator` usa `AGENT_PLANNING_EVALUATOR_MODEL`.
- `domain-critic` usa `AGENT_DOMAIN_CRITIC_MODEL`.
- `completions` usa `AGENT_FINAL_MODEL` (salvo override en request).
- `insights` usa `AGENT_INSIGHTS_MODEL`.
- `embeddings` usa `AGENT_EMBEDDING_MODEL`.

## 7. Flujo de arranque
1. Inicia FastAPI con lifespan v2.
2. Resuelve `AGENTS_OLLAMA_KEEP_ALIVE`.
3. Evalúa preferencia/disponibilidad de GPU.
4. Crea `V2RuntimeServices` con cliente Ollama compartido.
5. Ejecuta `download_models()` para asegurar disponibilidad de modelos.
6. Expone endpoints `v2/*`.

## 8. Configuracion de entorno

Runtime:
- `AGENTS_OLLAMA_KEEP_ALIVE` (default `0s`)
- `AGENTS_OLLAMA_PREFER_GPU` (default `true`)
- `NVIDIA_VISIBLE_DEVICES` (opcional)

Modelos:
- definidos en `.env`/`.env.example` y resueltos por `src/models/registry.py`.

## 9. Manejo de errores
Comportamiento general:
- errores de runtime/servicio se mapean a `HTTP 503` en la mayoría de endpoints de inferencia,
- errores de embeddings retornan `HTTP 400` (entrada vacía) o `HTTP 500` (fallo de ejecución),
- `runtime_services_unavailable` se devuelve cuando el servicio aún no completó su inicialización.

## 10. Observabilidad basica
Durante startup se registran:
- `keep_alive`,
- preferencia de GPU,
- disponibilidad detectada de GPU,
- descarga/omisión de modelos.

Además, `GET /v2/health` permite probes de orquestación.

## 11. Publico objetivo de esta documentacion
Esta guía está orientada a un público general técnico (producto, integración y operación básica) que necesita entender:
- qué hace el servicio,
- qué endpoints ofrece,
- cómo configurarlo,
- cómo se conecta con el resto de la plataforma.

Para detalle interno de arquitectura, contratos formales y flujos de control, consultar `TECHNICAL_DOCUMENTATION_AGENTS.md`.
