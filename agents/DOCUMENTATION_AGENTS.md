# Servicio Agents (Ollama Runtime)

## 1. Nombre del servicio
Agents Runtime API

## 2. Descripcion
Servicio FastAPI que actua como runtime local de modelos en Ollama para:
- chat conversacional general (v1),
- decision y evaluacion estructurada para ciclos agenticos (v2),
- healthcheck y metadatos operativos.

El proceso levanta Ollama en el mismo contenedor y expone API HTTP en puerto 8003.

## 3. Rol dentro del sistema
- Servir inferencia local para otros servicios internos.
- Descargar/preparar modelos requeridos al iniciar.
- Ejecutar llamadas de inferencia con control de concurrencia para evitar contencion de VRAM/RAM.
- Publicar endpoints de estado (`/v1/health`) y metadatos (`/v1/info`).
- Ser el runtime primario consumido de forma directa por `agent_core` para:
  - generacion final de respuesta,
  - evaluacion de suficiencia,
  - extraccion de insights.

## 4. Arquitectura de alto nivel
- Framework: FastAPI.
- Runtime de modelos: Ollama (proceso `ollama serve` en el mismo contenedor).
- Router principal:
  - prefijo `/v1` para chat/info/health,
  - prefijo `/v2` para decision/evaluacion estructurada.
- Inicializacion:
  - `lifespan` de v1 detecta GPU, calcula `keep_alive` y descarga modelos faltantes.

## 5. Endpoints expuestos

### 5.1 Endpoints v1
- `POST /v1/completions`
  - Entrada: `CompletionRequest`
    - `history: List[Dict[str, str]]`
    - `temperature: float` (default 0.7)
    - `max_tokens: int` (default 512)
  - Flujo:
    - delega a `ChatService.chat()`.
    - `ChatService` llama `ollama.chat(...)` con lock global y `keep_alive` configurable.
    - este endpoint es el contrato principal para llamadas directas desde `agent_core`.
  - Salida: texto de respuesta del modelo (`response["message"]["content"]`).

- `GET /v1/info`
  - Devuelve metadata del runtime:
    - `service`
    - `ChatService.Model`
    - `ChatService.Version`
    - `policy_version`

- `GET /v1/health`
  - Respuesta simple: `{"status": "ok"}`.

### 5.2 Endpoints v2
- `POST /v2/decision`
  - Entrada: `DecisionModelInput`
    - query/intencion/contexto/historial/tool catalog/attempt.
  - Funcion:
    - construye prompt estructurado.
    - llama modelo Ollama.
    - extrae JSON del output y valida con Pydantic.
  - Salida: `DecisionModelOutput`
    - `action`, `tool_name`, `tool_arguments`, `confidence`, `reasoning`.

- `POST /v2/evaluate`
  - Entrada: `EvaluatorModelInput`
    - query, tool_name, tool_result, propiedades esperadas, intent, contexto acumulado.
  - Funcion:
    - construye prompt de rubrica de suficiencia/error.
    - llama modelo Ollama.
    - parsea JSON y valida.
  - Salida: `EvaluatorModelOutput`
    - `evaluation` en `sufficient|insufficient|recoverable_error|terminal_error`
    - `confidence`, `reasoning`, `missing_properties`.

## 6. Endpoints externos utilizados por este servicio
Este servicio no llama otros microservicios HTTP del proyecto. Sus dependencias externas son:

- API local de Ollama (via SDK Python `ollama`):
  - `ollama.list()` para inventario de modelos instalados.
  - `ollama.pull(model)` para descargar modelos faltantes.
  - `ollama.chat(...)` para inferencia en v1 y v2.

- Comando del sistema:
  - `nvidia-smi -L` para detectar GPU disponible.

Notas:
- Si `AGENTS_OLLAMA_PREFER_GPU=true` y no se detecta GPU, el servicio registra warning y continua en CPU.
- En Docker, la reserva de GPU esta declarada en `docker-compose.yml` para el servicio `agents`.

## 7. Consumidores externos de este servicio
El consumidor principal actual es `agent_core`:
- `agent_core` usa `POST http://agents:8003/v1/completions` con payload `history`.
- El postprocesamiento de texto (limpieza de etiquetas/artefactos) se realiza en el consumidor (`agent_core`),
  manteniendo este servicio como runtime de inferencia puro.

El frontend no llama este servicio directamente en el flujo principal; se comunica con `agent-core`.

## 8. Flujo operativo detallado

### 8.1 Arranque
1. Se levanta FastAPI con `lifespan` de v1.
2. Se resuelve `keep_alive` desde entorno.
3. Se detecta preferencia GPU y disponibilidad real.
4. Se descargan modelos faltantes (con reintentos al listar modelos).
5. Se inicializa `InfoService`.

### 8.2 Inferencia v1 (`/v1/completions`)
1. Se recibe historial y parametros de generacion.
2. Se arma `options` (`temperature`, `num_predict`).
3. Se entra a `_ollama_chat_with_runtime`:
  - log `waiting_lock`,
  - lock global de proceso,
  - `ollama.chat(...)`,
  - log `lock_released` con latencia ms.
4. Se devuelve texto limpio de `message.content`.

### 8.3 Decision/Evaluacion v2
1. Se recibe payload estructurado.
2. Se construye prompt con reglas y formato JSON estricto.
3. Se llama `ollama.chat(...)`.
4. Se extrae objeto JSON del texto (incluye manejo de fences markdown).
5. Se valida contra esquema Pydantic de salida.
6. Se responde con objeto tipado o 503 si falla el modelo.

## 9. Modelos y seleccion
- Modelo de chat v1:
  - `WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M`.

- Modelo CIF (servicio auxiliar interno, no expuesto por endpoint):
  - `WilhelmBuitrago/llamat-3-cif-8b:Q5_K_M`.

- Modelo para decision/evaluacion v2:
  - configurable por `AGENTS_DECISION_MODEL`,
  - default: `yasserrmd/Qwen2.5-7B-Instruct-1M`.

- Lista de modelos precargados en arranque (`LoadModelsService`):
  - `yasserrmd/Qwen2.5-7B-Instruct-1M`
  - `WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M`
  - `WilhelmBuitrago/llamat-3-cif-8b:Q5_K_M`

## 10. Concurrencia, rendimiento y estabilidad
- Lock global `_OLLAMA_MODEL_LOCK` serializa llamadas a `ollama.chat`.
- Objetivo: reducir riesgo de saturacion de recursos cuando multiples requests compiten.
- `AGENTS_OLLAMA_KEEP_ALIVE` controla politica de descarga/mantenimiento de modelo en memoria.
  - default recomendado actual: `0s` (descarga inmediata tras request).

Tradeoff:
- `0s` reduce uso persistente de memoria, pero puede aumentar latencia de requests sucesivos.

## 11. Manejo de errores
- v1:
  - Fallos de inferencia lanzan `RuntimeError("Chat model invocation failed: ...")`.

- v2:
  - Errores en modelo/parsing validacion retornan `HTTP 503` con detalle:
    - `decision_model_failed: ...`
    - `evaluator_model_failed: ...`

- Descarga de modelos:
  - errores por modelo se registran en log y el proceso continua.

## 12. Observabilidad
- Logs de runtime en inferencia:
  - `waiting_lock`
  - `lock_acquired`
  - `lock_released` (incluye `elapsed_ms`)

- Logs de startup:
  - `keep_alive`, `gpu_requested`, `gpu_detected`.

- Health endpoint:
  - `GET /v1/health` para probes de Docker Compose.

## 13. Variables de entorno
- `AGENTS_OLLAMA_KEEP_ALIVE`
  - politica de retencion del modelo en Ollama (ej. `0s`, `5m`).

- `AGENTS_OLLAMA_PREFER_GPU`
  - `true/false` para preferencia de GPU.

- `AGENTS_DECISION_MODEL`
  - modelo de v2 (decision/evaluacion).

- `NVIDIA_VISIBLE_DEVICES`
  - usada en deteccion de GPU y runtime Docker NVIDIA.

## 14. Despliegue (Docker)
- Imagen base: `ollama/ollama:latest`.
- Se instala Python y dependencias (`fastapi`, `uvicorn`, `ollama`, etc.).
- Comando de inicio:
  - levanta `ollama serve`,
  - hace `ollama pull` del modelo de decision por variable,
  - levanta `uvicorn api.app:app --port 8003`.

## 15. SSE y streaming
Este servicio actualmente no implementa SSE ni streaming chunked en endpoints publicos.

Comportamiento actual:
- `POST /v1/completions` retorna respuesta unica (texto final).
- `POST /v2/decision` y `POST /v2/evaluate` retornan JSON unico.


