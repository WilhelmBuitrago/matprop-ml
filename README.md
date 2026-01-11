# MatProp-ML 🧪🤖

**MatProp-ML** es un **chatbot interactivo para ciencia e ingeniería de materiales**, diseñado para que el usuario consulte materiales, propiedades y conceptos técnicos de forma conversacional, pero con ejecución **estructurada y controlada** detrás de escena.

El foco del proyecto no es académico, sino **utilitario**: permitir que un usuario haga preguntas reales de materiales y obtenga respuestas accionables, apoyadas en herramientas formales y modelos especializados.

---

## 🚀 ¿Qué puede hacer actualmente?

✔️ **Chatbot especializado en materiales**  
- Basado en **LLaMat-3**, un modelo derivado de *LLaMA‑3* finetuneado para ciencia de materiales.  
- Modelo: 🔗 `WilhelmBuitrago/llamat-3-chat-8b` (Ollama)

🧠 **Orquestación inteligente de herramientas**  
- Planeación automática mediante **Qwen2.5‑7B‑Instruct**.  
- El modelo decide *qué hacer*, *en qué orden* y *con qué argumentos*.

🧰 **Herramientas disponibles**  
- 🔍 `search_materials` (por ID o fórmula química)  
- 📊 `get_material_properties` (propiedades específicas)  
- 🧠 `delegate_to_reasoner` (explicaciones conceptuales)

⚙️ **Backend robusto**  
- Implementado en **Python**.  
- API basada en **FastAPI**.  
- Inferencia local mediante **Ollama**.

🎨 **Frontend moderno**  
- Basado en **Next.js + React** (arquitectura web moderna orientada a UX).

🔒 **Ejecución controlada**  
- El modelo conversacional **no ejecuta acciones directamente**.  
- Todo pasa por validación de esquemas JSON.

---

## 🧩 Arquitectura y orquestación de modelos

El sistema sigue una arquitectura **multi‑modelo por roles**:

## 📂 Estructura del proyecto

```
.
├── agent_core/
│   ├── src/
│   │   ├── api/v1/service.py
│   │       └── CompletionService
│   │   ├── tools/
│   │       ├── config.py 
│   │       └── tools.py
│   └── ...
│
├── agents/
│   └── src/api/v1/service.py
│       ├── LoadModelsService       # Descarga automática de modelos
│       ├── PlanningService         # Qwen2.5 (planner)
│       ├── ChatService             # LLaMat‑3 (chat)
│       ├── CifService              # Generación CIF
│       └── InfoService             # Información del proyecto
│
├── backend_llm/
│   └── src/
│       ├── chat_agent.py           # Backend de conversación
│       └── config.py               # Configuracion de cache de conversacion
│
├── frontend/
│   ├── src/app/
│   │   ├── components/             # Componentes principales 
│   │   ├── configuration/          # Configuraciones principales
│   │   └── ...
│   └── ...
│
├── docker-compose.yml
├── Dockerfile
└── README.md
```

---

## 🐳 Ejecución con Docker

### Requisitos

⚠️ **GPU altamente recomendada (prácticamente obligatoria)**

- GPU NVIDIA con **≥ 8 GB de VRAM**  
  *(modelos 8B y 7B cuantizados Q5_K_M / Q6_K)*

👉 **Ejecución solo en CPU**:
- Carga secuencial de modelos ≈ **12–14 GB RAM**
- RAM recomendada en CPU: **≥ 16 GB** (ideal ≥ 24 GB)
- Rendimiento limitado

### Levantar el stack

```bash
docker compose up --build
```

Servicios:
- Ollama
- Agent‑Core
- Agent‑Policy (planner)

Los modelos se descargan automáticamente si no existen.

## ⚠️ Consideraciones importantes

- Los resultados **pueden contener errores**.
- Toda salida generada por IA debe ser **verificada**.
- El sistema **no reemplaza** bases de datos oficiales ni simulaciones ab initio.
- Diseñado como **herramienta de apoyo**, no como fuente única de verdad.

---

## 🛠️ Estado del proyecto

🚧 **Activo / en desarrollo**

Próximos pasos:
- 🔬 Integración de **predicción de propiedades con MEGNet**
- 🧠 Nuevas herramientas para ampliar contexto
- 📈 Más propiedades físicas
- 🔗 Conexión a bases de datos reales (Materials Project, OQMD)

---