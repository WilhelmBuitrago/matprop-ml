CRÍTICO - Secreto/API key hardcodeada en código fuente
Problema: La clave de Materials Project está embebida en el código, lo que expone credenciales, rompe seguridad operativa y dificulta rotación.
Mejora general: Externalizar secretos y aplicar gestión de credenciales por entorno.
Mejora directa: Mover la API key a variable de entorno/secret manager, agregar validación de presencia al arranque, y eliminar cualquier key del historial Git.
Referencias: tools.py:125, tools.py:219

CRÍTICO - Contrato de herramientas inconsistente con implementación
Problema: Se publican herramientas en el schema que no existen en el ejecutor real, causando planes válidos para el planner pero errores en runtime.
Mejora general: Alinear catálogo de herramientas expuestas con herramientas realmente implementadas.
Mejora directa: Mantener el esquema de config.py pero limitando el llamado a solo las herramientas validas ya implementadas actualmente.
Referencias: config.py:212, config.py:277, config.py:317, service.py:20

CRÍTICO - Bug de contrato de chat entre backend_llm y ChatAgent
Problema: El endpoint envía una lista de mensajes, pero el método está tipado como string y luego itera/apendea elemento por elemento; se corrompe historial y conteo de tokens.
Mejora general: Unificar modelo de datos de conversación de extremo a extremo.
Mejora directa: Definir un único formato de entrada (lista de mensajes o mensaje único), ajustar tipado y lógica de append/tokenización para ese formato.
Referencias: app.py:24, app.py:88, chat_agent.py:228, chat_agent.py:240, chat_agent.py:244

CRÍTICO - Llamadas HTTP internas sin timeout/retry/circuit-breaker
Problema: Varias llamadas entre servicios no tienen timeout ni política de resiliencia; un servicio lento puede bloquear cadena completa.
Mejora general: Estandarizar cliente HTTP robusto para comunicación interna.
Mejora directa: Definir timeout corto, retries con backoff, control de errores por tipo y fallback explícito por endpoint.
Referencias: service.py:35, service.py:69, router.py:31, router.py:37, router.py:43

CRÍTICO - Conexiones hardcodeadas con localhost incompatibles con despliegue por contenedores
Problema: El proxy de agent_core llama a localhost:8001; en Docker esto apunta al contenedor local, no al servicio backend-llm.
Mejora general: Configuración de endpoints por entorno y DNS de servicio.
Mejora directa: Parametrizar URLs internas y usar nombres de servicio de la red Docker para tráfico interno.
Referencias: router.py:31, docker-compose.yml:66

CRÍTICO - Validación/parsing de plan con posibilidad de crash
Problema: Se accede a parsed_steps[-1] sin garantizar que la lista tenga elementos; además la lógica de valids no marca casos ya válidos y puede fallar la convergencia.
Mejora general: Endurecer pipeline de validación con invariantes explícitos.
Mejora directa: Validar lista no vacía antes de indexar, y corregir criterios de éxito para pasos ya conformes al schema.
Referencias: service.py:324, service.py:328

ALTO - Schema JSON mal definido (error de clave)
Problema: En definición de parámetros aparece type: con sintaxis incorrecta; invalida/rompe validación y normalización de argumentos.
Mejora general: Validar todos los schemas en CI.
Mejora directa: Corregir estructura JSON Schema, ejecutar tests de contrato y agregar lint de schemas.
Referencias: config.py:183

ALTO - Diseño de API obliga filtros cuando la implementación los trata como opcionales
Problema: En schema material requiere filters, pero en código filters tiene default vacío; incoherencia de contrato.
Mejora general: Sincronizar contrato público y semántica de implementación.
Mejora directa: Definir claramente si filters es opcional; ajustar required y documentación en ambos lados.
Referencias: config.py:132, tools.py:123

ALTO - Mutación de input en tool de propiedades
Problema: Se modifica la lista de propiedades recibida (append), generando efectos laterales difíciles de rastrear.
Mejora general: Evitar mutaciones de argumentos de entrada.
Mejora directa: Trabajar sobre copia local inmutable y normalizar nomenclatura de campos.
Referencias: tools.py:177

ALTO - Error funcional en visualización de estructura
Problema: Se normaliza material a dict y luego se pasa ese dict a get_structure_by_material_id, que espera un id string.
Mejora general: Asegurar compatibilidad de tipos al cruzar utilidades.
Mejora directa: Extraer material_id normalizado como string antes de invocar MPRester.
Referencias: tools.py:220, tools.py:221

ALTO - CORS inseguro e inconsistente con credenciales
Problema: allow_origins con * combinado con credenciales habilitadas es inseguro y en navegadores modernos es conflictivo.
Mejora general: Política CORS por whitelist de dominios.
Mejora directa: Definir lista de orígenes permitidos por entorno y desactivar credenciales donde no se requieran.
Referencias: app.py:9, app.py:10, app.py:31, app.py:32

ALTO - Descarga de modelos en arranque bloquea disponibilidad
Problema: El lifespan descarga modelos al inicio; puede tardar mucho y afectar readiness/health.
Mejora general: Separar warmup pesado del startup crítico.
Mejora directa: Mover descarga a proceso asíncrono/background y exponer estado de preparación.
Referencias: router.py:24

ALTO - Archivo con doble implementación de clase en loader
Problema: Existen dos clases ModelLoader en el mismo archivo, con código duplicado/obsoleto y ramas inconsistentes.
Mejora general: Consolidar una sola implementación canónica.
Mejora directa: Eliminar implementación antigua, conservar una versión, y cubrir con tests de regresión de carga/predicción.
Referencias: loader.py:12, loader.py:122

ALTO - Pérdida de información en construcción de layout de modelos con splits
Problema: Solo se conserva el primer set de archivos por split, descartando potencialmente otros submodelos.
Mejora general: Preservar estructura completa de artefactos por split.
Mejora directa: Guardar todas las entradas de submodels por split y validar cardinalidad esperada.
Referencias: build_layout.py:108

ALTO - Estado global compartido sin control de concurrencia
Problema: Uso de singleton global agent en backend_llm expone condiciones de carrera y mezcla de sesiones en alta concurrencia.
Mejora general: Diseñar estado por sesión/usuario o almacenamiento externo thread-safe.
Mejora directa: Introducir sesión explícita, lock o store concurrente y política de aislamiento conversacional.
Referencias: app.py:61, app.py:82, app.py:113

MEDIO - Endpoint que modifica estado usando GET
Problema: clear_history se expone por GET (no idempotencia semántica REST y riesgo de invocación accidental por crawlers/prefetch).
Mejora general: Corregir semántica HTTP para operaciones de mutación.
Mejora directa: Cambiar a POST/DELETE y exigir confirmación/intención explícita.
Referencias: router.py:36, app.py:100

MEDIO - Frontend con manejo de entorno inconsistente
Problema: Se usa non-null assertion en ENV y en otras páginas process.env directo; puede romper en build/runtime según entorno.
Mejora general: Centralizar acceso a configuración cliente.
Mejora directa: Unificar consumo de variables en un módulo validado con fallback controlado y mensaje de error de configuración.
Referencias: env.client.ts:3, page.tsx:11, page.tsx:11

MEDIO - Degradación de rendimiento por renderizado carácter a carácter
Problema: El efecto de escritura realiza muchos setState secuenciales, costoso en respuestas largas.
Mejora general: Estrategia de streaming por chunks o intervalos adaptativos.
Mejora directa: Bufferizar salida y actualizar UI por bloques temporizados, no por cada carácter.
Referencias: ChatWindow.tsx:75

MEDIO - Artefactos de código en desuso / baja higiene
Problema: Imports no usados y redefiniciones reducen legibilidad y elevan riesgo de errores.
Mejora general: Política de lint estricta y limpieza continua.
Mejora directa: Activar reglas de no-unused-imports y dead-code en CI, y limpiar bloques heredados.
Referencias: service.py:2, router.py:10, config.py:2

MEDIO - Nombre de archivo de inicialización de paquete incorrecto
Problema: Existe __init_.py en vez de init.py; puede afectar descubrimiento de paquete/herramientas.
Mejora general: Estandarización de estructura Python package.
Mejora directa: Renombrar al nombre estándar y verificar empaquetado/imports.
Referencia: SOURCES.txt:2

MEDIO - Dependencia de red externa en tests sin aislamiento robusto
Problema: Tests de descarga dependen de GitHub/red y de timestamps, lo que los vuelve frágiles/no deterministas.
Mejora general: Diferenciar tests unitarios (mock) de integración (red real).
Mejora directa: Mockear requests en unit tests y dejar pruebas de red en suite separada, con tolerancias temporales.
Referencias: test_download_megnet.py:31, test_download_megnet.py:46

Adicional: Cubre todos los issues de este problema, para clear_history cambia el metodo GET a POST y manten GET temporalmente como deprecated, has un rediseño completo por sesión/usuario. Alinea versiones entre servidores con pining moderado y acualiza DOCUMENTATION:md por servicio en la misma fase.