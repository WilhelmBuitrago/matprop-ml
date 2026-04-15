# MatProp-ML

![Estado](https://img.shields.io/badge/status-en%20desarrollo-orange)
![Licencia](https://img.shields.io/badge/license-MIT-green)
![LLaMat-3](https://img.shields.io/badge/modelo-LLaMat--3-blue)
![Reasoning](https://img.shields.io/badge/reasoning-DeepSeek--R1-0ea5e9)
![Frontend](https://img.shields.io/badge/frontend-Next.js%2014-black?logo=next.js)
![Local](https://img.shields.io/badge/infraestructura-local-green)

**Tu copiloto para preguntas de ciencia de materiales.**

Pregunta en lenguaje natural y obtén respuestas inteligentes sobre propiedades de materiales, búsqueda en literatura científica y generación de estructuras cristalinas — todo en tu máquina, sin depender de servidores externos.

> **Diferenciador clave:** El sistema "piensa" antes de responder. Usa modelos de razonamiento (DeepSeek-R1) para planear qué herramientas usar, ejecuta búsquedas, valida resultados, y te muestra cada paso. No es una caja negra.

---

## 💡 Ejemplo Rápido

```
👤 Tú:     "Find semiconductors with bandgap between 1.3 and 1.8 eV suitable for solar cells"

🤖 Sistema:
   1. Busca en base de datos de materiales
   2. Valida restricciones de bandgap
   3. Cruza con literatura sobre aplicaciones solares
   4. Retorna: CdTe, CIGS, GaAs (con propiedades específicas)
   5. Te muestra papers relacionados
   
✓ Resultado: Listo para tu análisis siguiente
```

---

## 🤔 ¿Qué es?

MatProp-ML es un **chatbot especializado en ciencia de materiales** que:

- **Entiende preguntas en lenguaje natural** sobre materiales (propiedades, aplicaciones, comportamiento)
- **Busca en múltiples fuentes**: base de datos de materiales, literatura científica, papers de arXiv
- **Genera estructuras cristalinas** en formato CIF (Crystallographic Information File)
- **Valida restricciones** para verificar si un material cumple criterios específicos
- **Te muestra el razonamiento** — ves cómo llegó a la conclusión

Todo corre **localmente en tu infraestructura** (Ollama + FastAPI + Next.js). Nada sube a la nube.

---

## ⭐ ¿Por qué usarlo?

- **💬 Menos fricción**: escribe preguntas normales, obtén respuestas útiles. Sin formularios complicados, sin "traducir" a jerga de API.

- **🧠 Razonamiento visible**: el sistema te muestra cómo pensó. Buscó en BD → validó restricciones → consultó literatura → concluyó. Confía más porque ves el camino.

- **📚 Búsqueda multimodal**: no eliges entre "buscar materiales" o "buscar papers" — todo en un solo lugar con contexto conectado.

- **🔍 Trazabilidad completa**: cada pregunta, cada búsqueda, cada decisión queda registrada en trazas. Útil para reproducibilidad y debugging.

- **🏠 100% local**: tu máquina, tus datos. Sin vendor lock-in, sin preocupaciones de privacidad.

- **👨‍🔬 Diseñado para académicos**: el modelo base (LLaMat-3) fue finetuned específicamente en ciencia de materiales, no es "ChatGPT genérico".

---

## 🚀 Quickstart

### Requisitos Mínimos
- **Docker & Docker Compose**
- **GPU recomendada** (Nvidia + CUDA), pero CPU funciona
- **8GB RAM mínimo**, 16GB+ óptimo

### Pasos (3 únicamente)

**1. Clona el repositorio:**
```bash
git clone https://github.com/WilhelmBuitrago/matprop-ml.git
cd matprop-ml
```

**2. Inicia todo con Docker:**
```bash
docker compose up --build
```

La **primera ejecución tarda 5-10 minutos** (Ollama descarga modelos automáticamente).

**3. Abre en tu navegador:**
```
http://localhost:3000
```

¡Listo! Prueba escribiendo una pregunta. Ejemplo:

> "What are the thermal properties of silicon carbide at high temperatures?"

---

## ✨ Qué Puedo Hacer

### 🔬 Búsqueda de Materiales por Propiedades
```
"Find all semiconductors with direct bandgap between 2.0 and 3.0 eV"
→ Sistema busca en BD, valida restricciones, retorna opciones con referencias
```

### 🏗️ Generar Estructuras Cristalinas
```
"Generate the crystal structure of perovskite CH3NH3PbI3"
→ Sistema crea archivo CIF, explica parámetros de red, sugiere validación
```

### 📖 Buscar Literatura Relacionada
```
"Find recent papers on defects in titanium dioxide"
→ Busca en Semantic Scholar + arXiv, rankea por relevancia, extrae insights
```

### ✅ Validar Restricciones de Diseño
```
"Is graphene suitable for thermal conductivity applications at room temperature?"
→ Sistema consulta literatura, evalúa restricciones, retorna análisis fundado
```

### 🔍 Análisis Profundo de Papers
```
"What does the literature say about dopants in gallium nitride?"
→ Descarga papers, extrae secciones relevantes, resume insights principales
```

---

## 🧠 Cómo Funciona (el "Thinking" Magic)

Cuando haces una pregunta, MatProp-ML sigue este flujo:

```
Tu pregunta
    ↓
1️⃣  PLANEACIÓN: DeepSeek-R1 "piensa" → ¿Qué herramientas necesito?
    (Búsqueda en BD? Literatura? Generación de estructura?)
    ↓
2️⃣  EJECUCIÓN: Ejecuta las herramientas seleccionadas
    (Busca, valida, genera, consulta papers)
    ↓
3️⃣  EVALUACIÓN: Valida resultados → ¿Es suficiente? ¿Necesito más info?
    (Si no, replantea y busca de nuevo)
    ↓
4️⃣  REDACCIÓN FINAL: Genera respuesta clara en lenguaje natural
    ↓
✓ Respuesta lista (con razonamiento visible)
```

**Esto te da:**
- **Visibilidad**: ves cada paso (logs detallados en terminal)
- **Confiabilidad**: si algo falló, ves dónde
- **Reproducibilidad**: puedes validar el proceso

No es "magia negra" — es razonamiento estructurado.

---

## ⚠️ Limitaciones (Importante Leer)

Este es un **sistema en desarrollo**. Úsalo responsablemente:

### Capacidades
- ✅ Búsqueda de materiales por propiedades (bueno)
- ✅ Consulta de literatura científica (bueno)
- ✅ Generación de estructuras cristalinas (útil para prototipado)
- ✅ Validación de restricciones básicas (aceptable)

### Limitaciones
- ⚠️ **Modelo base 8B**: rápido pero no ultra-preciso. Gap en áreas especializadas.
- ⚠️ **Datos de entrenamiento finitos**: LLaMat-3 cubre ciencia de materiales general, pero puede tener gaps en áreas nuevas o muy específicas.
- ⚠️ **Puede cometer errores**: el sistema puede retornar respuestas plausibles pero incorrectas.
- ⚠️ **No reemplaza simulaciones**: para decisiones críticas, valida siempre con métodos experimentales o simulaciones (DFT, etc).
- ⚠️ **GPU recomendada**: en CPU funciona pero es lento (minutos por respuesta).

### Uso Responsable
✋ **Antes de usar en publicaciones**, verifica resultados con fuentes independientes.
✋ **Úsalo como herramienta**, no como autoridad. Es complemento a tu expertise, no sustituto.
✋ **Reporta bugs** en [GitHub Issues](https://github.com/WilhelmBuitrago/matprop-ml/issues) — nos ayudas a mejorar.

---

## 📚 Documentación Técnica

Para profundizar según tu rol:

- **Usuario final que quiere configurar modelos:** 
  → `agent_core/DOCUMENTATION_AGENT_CORE.md`

- **Investigador que quiere entender arquitectura:**
  → `agent_core/TECHNICAL_DOCUMENTATION_AGENT_CORE.md`

- **Desarrollador trabajando con runtime de modelos:**
  → `agents/DOCUMENTATION_AGENTS.md` + `agents/TECHNICAL_DOCUMENTATION_AGENTS.md`

- **Frontend UI customization:**
  → `frontend/DOCUMENTACION_FRONTEND.md`

- **Changelog y versiones:**
  → `CHANGELOGS.md`

---

## 🔧 Configuración (Para Usuarios Avanzados)

### Cambiar Modelos

Edita `.env` en la raíz:

```bash
# Modelo base (respuesta final)
AGENT_BASE_MODEL=deepseek-r1:8b

# Modelos de razonamiento (planeación y evaluación)
AGENT_PLANNING_EVALUATOR_MODEL=deepseek-r1:8b
AGENT_PLANNER_MODEL=deepseek-r1:8b
AGENT_EVALUATOR_MODEL=deepseek-r1:8b

# Modelo especializado para generar estructuras CIF
AGENT_CIF_MODEL=WilhelmBuitrago/llamat-3-cif-8b:Q5_K_M

# Modelo de embeddings (búsqueda semántica)
AGENT_EMBEDDING_MODEL=mxbai-embed-large
```

### GPU vs CPU

```bash
# Preferir GPU si está disponible
AGENTS_OLLAMA_PREFER_GPU=true

# Especificar dispositivos NVIDIA (dejar vacío para todos)
NVIDIA_VISIBLE_DEVICES=0,1
```

### API Keys (Opcional para Búsqueda Mejorada)

Para acceso a literatura más amplia:

```bash
# Semantic Scholar (para búsqueda de papers)
SEMANTIC_SCHOLAR_API_KEY=your_key

# Material Project (para BD de materiales)
MP_API_KEY=your_key

# UnPaywall (para acceso a papers)
UNPAYWALL_EMAIL=your_email@example.com
```

---

## 🏗️ Estructura del Proyecto

```text
matprop-ml/
│
├─ frontend/                      # UI (Next.js 14)
│  ├─ src/app/components/        # Componentes React
│  └─ DOCUMENTACION_FRONTEND.md
│
├─ agent_core/                    # Orquestación (FastAPI)
│  ├─ src/api/v4/                # Endpoint principal /v4/completions
│  ├─ src/tools/catalog/         # 5 herramientas especializadas
│  │  ├─ query_materials/
│  │  ├─ generate_structure/
│  │  ├─ validate_material_constraints/
│  │  ├─ search_scientific_documents/
│  │  └─ document_rag/
│  ├─ DOCUMENTATION_AGENT_CORE.md
│  └─ TECHNICAL_DOCUMENTATION_AGENT_CORE.md
│
├─ agents/                        # Runtime de modelos (FastAPI + Ollama)
│  ├─ src/api/v2/                # Endpoints de modelos
│  ├─ src/services/              # Servicios especializados
│  ├─ DOCUMENTATION_AGENTS.md
│  └─ TECHNICAL_DOCUMENTATION_AGENTS.md
│
├─ services/                      # Servicios internos (no público)
│  └─ evaluation_service/
│
├─ docker-compose.yml             # Stack completo
├─ docker-compose-development.yml # Stack desarrollo
│
└─ README.md                      # Este archivo
```

---

## 📡 Servicios Públicos

Estos son los servicios disponibles para integración:

| Servicio | Puerto | Rol |
|----------|--------|-----|
| **Frontend** | `3000` | UI conversacional |
| **Agent Core** | `8004` | Orquestación + trazabilidad |
| **Agents Runtime** | `8003` | Modelos + herramientas |

### Consumir la API Directamente

Si quieres integrar en tu código (sin UI):

```bash
curl -X POST http://localhost:8004/v4/completions \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find silicon with bandgap > 1 eV",
    "max_iterations": 8,
    "max_tool_calls": 8,
    "stream": false
  }'
```

Response:
```json
{
  "id": "req-xyz",
  "choices": [{"text": "Silicon has a direct bandgap of 1.12 eV..."}],
  "usage": {"tokens": 256},
  "metadata": {
    "policy_mode": "planned",
    "iterations_count": 3,
    "stop_reason": "complete"
  }
}
```

---

## 🚀 Despliegue en Producción

Para entornos de producción (fuera del scope de este README), considera:

- Ejecutar en máquina con GPU dedicada
- Configurar logs centralizados (ELK, Datadog, etc)
- Monitoreo de salud (health checks)
- Rate limiting en API Gateway
- Validación de entrada robusta

Consulta `TECHNICAL_DOCUMENTATION_AGENT_CORE.md` para detalles.

### Seguridad mínima recomendada (Agent Core)

- Activar `AGENT_AUTH_MODE=api_key` en entornos no locales.
- Configurar rate limit con `AGENT_RATE_LIMIT_ENABLED`, `AGENT_RATE_LIMIT_MAX_REQUESTS` y `AGENT_RATE_LIMIT_WINDOW_SECONDS`.
- No versionar secretos en `.env`; usar variables de entorno del runtime.

---

## 🛣️ Roadmap

- [ ] Soporte para más modelos especializados (química computacional)
- [ ] Integración con simuladores (VASP, LAMMPS)
- [ ] Dashboard de métricas y análisis
- [ ] API de WebSocket para streaming mejorado
- [ ] Versiones quantizadas para CPU más accesible

---

## 📄 Licencia

MIT. Ver `LICENSE` para detalles completos.

---

## 🤝 Contribuir

Reporta bugs, sugiere features, o contribuye código en:
**https://github.com/WilhelmBuitrago/matprop-ml**

---

## 📞 Soporte

- **Bug reports**: [GitHub Issues](https://github.com/WilhelmBuitrago/matprop-ml/issues)
- **Documentación técnica**: Lee los archivos `TECHNICAL_DOCUMENTATION_*.md` en cada servicio
- **Configuración**: Consulta `.env.example` en cada directorio

---

**Última actualización:** Apr 2026
**Estado:** En desarrollo — úsalo con precaución en contextos de investigación crítica.
