# Agent Core v3 - Documentación Técnica Completa

**Documento de Referencia Técnica para Desarrolladores e Implementadores**

---

## 1. Policy Engine Determinística (Detalle Completo)

### 1.1 Clasificación de Intent

La política utiliza heurísticas determinísticas basadas en palabras clave para clasificar la intención del usuario:

```python
def classify_intent(query: str) -> Intent:
    """
    Mapea query → Intent basado en cobertura de palabras clave.
    
    Intent Mapping:
    ├─ "compare" (compare, versus, vs) → Intent.COMPARE
    ├─ "constraint" (constraint, must, at least, less than) → Intent.CONSTRAINT_VALIDATION
    ├─ "document" (paper, document, literature) → Intent.DOCUMENT_RESEARCH
    ├─ "structure" (structure, cif, poscar, crystal) → Intent.STRUCTURE_GENERATION
    └─ default → Intent.MATERIAL_LOOKUP
    """
```

**Tabla de Clasificación:**

| Intent | Palabras Clave | Significado | Herramientas Candidatas |
|---|---|---|---|
| `MATERIAL_LOOKUP` | (default) | Usuario busca propiedades de materiales | query_materials, search_docs, generate_structure |
| `COMPARE` | compare, versus, vs | Comparar propiedades entre materiales | compare_materials, query_materials |
| `CONSTRAINT_VALIDATION` | constraint, must, at least, less than | Validar restricciones | validate_constraints, query_materials |
| `DOCUMENT_RESEARCH` | paper, document, literature | Investigación bibliográfica | search_documents, extract_insights |
| `STRUCTURE_GENERATION` | structure, cif, poscar, crystal | Generar estructura cristalina | generate_structure, query_materials |

### 1.2 Routing de Candidatos por Intent

Después de clasificación, se generan candidatos de herramientas válidas:

```
MATERIAL_LOOKUP
├─ query_materials_database (primaria)
├─ search_scientific_documents (secundaria)
└─ generate_crystal_structure (terciaria)

COMPARE
├─ compare_materials (primaria)
└─ query_materials_database (secundaria)

CONSTRAINT_VALIDATION
├─ validate_material_constraints (primaria)
└─ query_materials_database (secundaria)

DOCUMENT_RESEARCH
├─ search_scientific_documents (primaria)
└─ extract_document_insights (secundaria)

STRUCTURE_GENERATION
├─ generate_crystal_structure (primaria)
└─ query_materials_database (secundaria)
```

### 1.3 Filtro por Precondiciones de Estado

Antes de scoring, solo sobreviven herramientas para las que `registry.can_run(tool, state)` retorna `True`:

```python
def can_run(tool: Tool, state: AgentState) -> bool:
    """Verifica si la herramienta tiene precondiciones satisfechas."""
    
    # Herramienta-específica:
    if tool == query_materials:
        return True  # Siempre disponible
    
    elif tool == validate_constraints:
        return (
            len(state.materials_found) > 0 and  # Requiere materiales
            len(state.constraints) > 0          # Requiere restricciones
        )
    
    elif tool == compare_materials:
        return len(state.materials_found) >= 2  # Requiere ≥2 materiales
    
    elif tool == extract_insights:
        return len(state.documents) > 0  # Requiere documentos
    
    # etc...
    
    return False
```

**Si ninguna herramienta sobrevive:** Loop termina con `stop_reason="no_valid_tools_available"`.

### 1.4 Scoring y Selección de Herramienta

El scoring combina 4 dimensiones con pesos fijos:

**Fórmula:**
```
score(tool, state) = w_missing × miss_coverage(tool, state)
                   + w_gain × info_gain(tool, state)
                   + w_compat × compatibility(tool, state)
                   - w_cost × cost(tool)

donde:
- w_missing = 0.45  (cubre información faltante)
- w_gain = 0.30     (gana información nueva)
- w_compat = 0.20   (compatible con intent)
- w_cost = 0.15     (costo computacional)
```

**Componentes Detallados:**

#### 1.4.1 Missing Information Coverage

```
miss_coverage(tool, state) ∈ [0, 1]

Se calcula según tipo de información:
├─ Materiales: 1.0 si state.materials_found vacío, 0.0 si >5
├─ Documentos: 1.0 si state.documents vacío, 0.0 si >10
├─ Propiedades: 1.0 si muchos campos null, 0.5 si algunos, 0.0 si completos
├─ Restricciones: 1.0 si none especificadas, 0.0 si validadas
└─ Insights: 1.0 si none extraídos, 0.0 si >3

Ejemplo:
- Si estado tiene 0 materiales → 1.0 (coverage máximo para query_materials)
- Si estado tiene 5+ materiales → 0.0 (coverage nulo)
```

#### 1.4.2 Information Gain

```
info_gain(tool, state) ∈ [0, 1]

Probabilidad de que ejecutar tool → información nueva:
├─ query_materials: 0.8 si ≤1 material, 0.3 si ≥2, 0.1 si ≥5
├─ search_documents: 0.9 si ≤2 docs, 0.5 si ≥3, 0.2 si ≥10
├─ extract_insights: 0.7 si docs sin insights, 0.3 si alguns, 0.0 si todos extraído
├─ validate_constraints: 1.0 si constraints pending, 0.0 si ya validado
└─ compare_materials: 0.6 si ≤2 materiales, 0.2 si ≥3, 0.0 si ≥10

Nota: Heurístico, basado en observación de saturación de información
```

#### 1.4.3 Compatibility

```
compatibility(tool, intent) ∈ [0, 1]

Score binario por mapping intent → tool:
├─ Perfect match: 1.0
├─ Secondary: 0.7
├─ Tertiary: 0.4
└─ Mismatch: 0.0

Tabla:
Intent MATERIAL_LOOKUP:
  ├─ query_materials: 1.0
  ├─ search_documents: 0.7
  └─ generate_structure: 0.4

Intent COMPARE:
  ├─ compare_materials: 1.0
  └─ query_materials: 0.7

Intent CONSTRAINT_VALIDATION:
  ├─ validate_constraints: 1.0
  └─ query_materials: 0.4

Intent DOCUMENT_RESEARCH:
  ├─ search_documents: 1.0
  └─ extract_insights: 0.7

Intent STRUCTURE_GENERATION:
  ├─ generate_structure: 1.0
  └─ query_materials: 0.5
```

#### 1.4.4 Cost

```
cost(tool) ∈ [0, 1]

Estimación normalizada de costo computacional:
├─ query_materials: 0.35        (API call + ranking, ~500ms)
├─ compare_materials: 0.20      (stub, <5ms)
├─ validate_constraints: 0.25   (local processing, ~30ms)
├─ search_documents: 0.55       (3 APIs paralelos, ~1500ms)
├─ extract_insights: 0.70       (LLM inference, ~1000ms)
└─ generate_structure: 0.40 (stub, <5ms)

La penalidad `- w_cost × cost(tool)` reduce score de herramientas caras
```

**Ejemplo Numérico de Scoring:**

Escenario: "Buscar materiales con band gap > 2.0 eV"
```
Query → Intent.MATERIAL_LOOKUP
Candidatos sobreviven precondiciones: todas

States:
├─ materials_found: []  (vacío)
├─ documents: [5 docs]  (no vacío)
└─ constraints: []

Scoring query_materials:
├─ miss_coverage = 1.0  (cero materiales = máxima cobertura)
├─ info_gain = 0.8     (probabilidad alta de info nueva)
├─ compatibility = 1.0  (perfect match para MATERIAL_LOOKUP)
├─ cost = 0.35
└─ score = 0.45×1.0 + 0.30×0.8 + 0.20×1.0 - 0.15×0.35
         = 0.45 + 0.24 + 0.20 - 0.0525
         = 0.8375 ✓

Scoring search_documents:
├─ miss_coverage = 0.5 (información secundaria, no primaria)
├─ info_gain = 0.4    (docs ya presentes)
├─ compatibility = 0.7 (secundaria)
├─ cost = 0.55
└─ score = 0.45×0.5 + 0.30×0.4 + 0.20×0.7 - 0.15×0.55
         = 0.225 + 0.12 + 0.14 - 0.0825
         = 0.4025

Selección: query_materials (0.8375 > 0.4025) ✓
```

### 1.5 Construcción Determinística de Argumentos

Después de seleccionar herramienta, se construyen argumentos de forma determinística:

```python
def _build_arguments(tool: Tool, state: AgentState, query: str) -> Dict:
    """Genera parámetros de entrada para la herramienta seleccionada."""
    
    # Por tipo de herramienta:
    
    if tool == query_materials:
        # Extraer material_id (mp-####) o formula de query
        match = re.search(r'mp-\d+', query)
        if match:
            return {"material_id": match.group()}
        
        # Sino, buscar fórmula química
        formula = extract_formula(query)  # Heurístico
        if formula:
            return {"formula": formula}
        
        # Fallback
        return {"formula": "Si"}  # Silicon por defecto
    
    elif tool == validate_constraints:
        # Usar constraints del estado o generar defaults
        if state.constraints:
            return {"constraints": state.constraints}
        
        # Default: estabilidad + band gap básico
        return {
            "constraints": [
                {"property": "is_stable", "operator": "==", "value": True},
                {"property": "band_gap", "operator": ">=", "value": 1.0}
            ]
        }
    
    elif tool == compare_materials:
        # Usar materiales ya encontrados (máx 5)
        return {
            "material_ids": [m.id for m in state.materials_found[:5]],
            "properties_to_compare": ["band_gap", "density", "energy_above_hull"]
        }
    
    elif tool == extract_insights:
        # Usar títulos de documentos
        return {
            "documents": [
                {"title": d.title, "abstract": d.abstract}
                for d in state.documents[:10]
            ],
            "focus_area": "material_properties"
        }
    
    elif tool == search_documents:
        # User query + material focus
        material_focus = None
        if state.materials_found:
            material_focus = state.materials_found[0].formula
        
        return {
            "query": query,
            "material_focus": material_focus,
            "max_results": 10
        }
    
    elif tool == generate_structure:
        # Material ID o fallback
        if state.materials_found:
            material_id = state.materials_found[0].id
        else:
            material_id = "mp-149"  # Silicon
        
        return {
            "material_id": material_id,
            "format": "cif"
        }
    
    return {}
```

---

## 2. Evaluador Acotado (Detalle Completo)

### 2.1 Rol del Evaluador

El evaluador es un **componente de calidad de evidencia**, NO de control:

```
Lo que NO hace:
├─ NO elige la herramienta siguiente
├─ NO modifica pesos o scores de policy
├─ NO fuerza acciones o re-iteraciones
└─ NO tiene control de flujo

Lo que SÍ hace:
├─ Emite señales estructuradas sobre calidad de evidencia
├─ Indica si información es "sufficient"
├─ Reporta "confidence" en la respuesta
├─ Documenta "missing_information" identificada
└─ Policy usa estas señales para decidir si continuar iterando
```

### 2.2 Contrato de Salida del Evaluador

```json
{
  "sufficient": false,
  "confidence": 0.65,
  "missing_information": ["comparison_data", "synthesis_conditions"],
  "reasoning": "Se han encontrado propiedades básicas pero faltan detalles de síntesis y comparación"
}
```

**Campos:**

| Campo | Tipo | Rango | Significado |
|---|---|---|---|
| `sufficient` | boolean | - | ¿La evidencia acumulada es suficiente para responder? |
| `confidence` | float | [0.0, 1.0] | Confianza en la respuesta (0=nada, 1=muy seguro) |
| `missing_information` | array[str] | - | Categorías de información faltante |
| `reasoning` | string | - | Explicación textual de la evaluación |

**Lógica de Decisión:**
```
Si sufficient == true:
  → Loop termina, construir respuesta final

Si sufficient == false:
  → Policy.decide() selecciona siguiente herramienta
  → Continuar iterando
```

### 2.3 Prompt del Evaluador

El evaluador se implementa como llamada a LLM remoto (Qwen2.5-7B). El prompt incluye:

```
SYSTEM:
"Eres un evaluador de calidad de evidencia científica. 
 Debes determinar si la evidencia recopilada es suficiente 
 para responder la consulta del usuario.
 
 Retorna JSON con estructura:
 {'sufficient': bool, 'confidence': float, 
  'missing_information': array, 'reasoning': str}"

USER:
"Consulta original: {user_query}

Herramienta ejecutada: {tool_name}

Salida de herramienta (truncada):
{tool_output_truncated}

Materiales conocidos:
{state.materials_found}

Documentos conocidos:
{state.documents_summaries}

¿Es la evidencia actual suficiente para responder?"
```

### 2.4 Robustez y Fallback

Si falla el endpoint remoto o el JSON parsing:

```python
def evaluate_with_fallback(context: EvaluationContext) -> EvaluatorFeedback:
    try:
        response = llm_client.complete(prompt, temperature=0.1)
        feedback = json.loads(response)
        validate_feedback_schema(feedback)
        return feedback
    
    except (ConnectionError, TimeoutError, JSONDecodeError):
        # Fallback: evaluación local conservadora
        return EvaluatorFeedback(
            sufficient=False,
            confidence=0.4,
            missing_information=["additional_evidence"],
            reasoning="fallback_evaluation"
        )
```

**Estrategia:** Fallback conservador - asume que más evidencia es mejor.

---

## 3. Loop Deterministico (Detalle Completo)

### 3.1 Orden Exacto de Ejecución por Iteración

```
1. Verificación de Continuación
   ↓ state.can_continue()
   └─ Verifica: max_iterations, max_tool_calls, max_context_tokens, max_wall_time_ms
   └─ Si algún límite excedido → STOP

2. Clasificación de Intent
   ↓ policy.classify_intent(query)
   └─ Determina Intent categoría

3. Filtro de Precondiciones
   ↓ registry.can_run() para cada herramienta
   └─ Elimina herramientas no disponibles
   └─ Si ninguna disponible → stop_reason="no_valid_tools_available"

4. Scoring y Selección
   ↓ policy.decide(state, intent, candidates)
   └─ Calcula score para cada candidata
   └─ Selecciona argmax(score)

5. Detección de Estancamiento
   ↓ si tool_selected == last_tool_selected en iteraciones recientes
   └─ stop_reason="stall_detected"

6. Construcción de Argumentos
   ↓ policy._build_arguments(tool, state, query)
   └─ Genera payload de entrada determinísticamente

7. Validación de Input
   ↓ registry.validate_input(tool, arguments)
   └─ Valida contra JSON schema
   └─ Si falla → stop_reason="tool_input_validation_failed"

8. Ejecución de Herramienta
   ↓ tool.execute(**arguments)
   └─ Timeout handling (default 30s)
   └─ Captura resultado y timestamps

9. Validación de Output
   ↓ registry.validate_output(tool, result)
   └─ Valida contra JSON schema
   └─ Si falla → stop_reason="tool_output_validation_failed"

10. Registro de Ejecución
    ↓ state.tool_calls.append(ToolExecutionRecord)
    └─ Persiste: tool_name, input, output, status, error_code, elapsed_ms

11. Mutación de Estado
    ↓ apply_tool_result(state, tool, result)
    └─ Agrega materials, documents, insights, constraints, etc.
    └─ Actualiza context_tokens_used

12. Evaluación de Evidencia
    ↓ evaluator.evaluate(state, result, query)
    └─ Retorna EvaluatorFeedback(sufficient, confidence, missing_info, reasoning)
    └─ Registra feedback en state.evaluator_feedback[]

13. Toma de Decisión
    ├─ Si feedback.sufficient == True
    │  → Ir a CONSTRUCCIÓN DO CONTEXTO FINAL
    ├─ Si max_iterations alcanzado
    │  → Ir a CONSTRUCCIÓN DE CONTEXTO FINAL (stop_reason="max_iterations")
    └─ Sino
       → Volver a Paso 1 (siguiente iteración)
```

### 3.2 Stop Reasons Soportados

**Por Límites de Presupuesto (AgentState.can_continue):**
```
- max_iterations: Número de iteraciones excedido
- max_tool_calls: Número de ejecutables herramientas excedido
- max_context_tokens: Contexto acumulado excedido
- max_wall_time_ms: Tiempo de ejecución total excedido
```

**Por Lógica de Loop:**
```
- sufficient_evidence: Evaluador indicó evidencia suficiente
- no_valid_tools_available: Ninguna herramienta pasó precondiciones
- stall_detected: Misma herramienta ejecutada N veces consecutivas
- tool_input_validation_failed: Argumentos inválidos
- tool_output_validation_failed: Resultado inválido
```

**Por Error de Herramienta:**
```
- {tool_error_code}: Si herramienta retorna error
  ├─ VALIDATION_ERROR
  ├─ API_ERROR
  ├─ PROVIDER_FAILURE
  ├─ AGENT_STATE_REQUIRED
  └─ UNEXPECTED_ERROR
```

**Fallback Final:**
```
- budget_exhausted: Si todos los límites se agotan sin terminar
```

---

## 4. Agent State (Detalle Completo)

### 4.1 Estructura

```python
class AgentState:
    """Fuente única de verdad para estadoagent en una request."""
    
    # Identificación
    request_id: str
    user_query: str
    
    # Presupuesto
    budget: BudgetTracker = {
        iterations_used: int,
        tool_calls_used: int,
        context_tokens_used: int,
        start_time: float,
        
        limits: {
            max_iterations: int,
            max_tool_calls: int,
            max_context_tokens: int,
            max_wall_time_ms: int
        }
    }
    
    # Evidencia Acumulada
    materials_found: List[MaterialRecord] = [
        {
            material_id: str,
            formula: str,
            properties: Dict[str, float]
        }
    ]
    
    documents: List[DocumentRecord] = [
        {
            doi: str,
            title: str,
            abstract: str,
            authors: List[str],
            publication_date: str,
            citations: int,
            provider: str,
            url: str
        }
    ]
    
    extracted_insights: List[Insight] = [
        {
            document_title: str,
            insights: List[str],
            fallback_used: bool
        }
    ]
    
    constraints: List[Constraint] = [
        {
            property: str,
            operator: str,  # >=, <=, ==, >, <, !=
            value: float | str | bool
        }
    ]
    
    properties_collected: Dict = {
        "constraint_validation": Optional[ValidationResult],
        "comparison": Optional[ComparisonResult],
        "structure": Optional[StructureData]
    }
    
    # Trazabilidad
    tool_calls: List[ToolExecutionRecord] = [
        {
            tool_name: str,
            tool_input: Dict,
            tool_output: Dict,
            status: str,  # "success" | "error"
            error_code: Optional[str],
            elapsed_ms: int
        }
    ]
    
    evaluator_feedback: List[EvaluatorFeedback] = [
        {
            sufficient: bool,
            confidence: float,
            missing_information: List[str],
            reasoning: str
        }
    ]
```

### 4.2 Métodos Críticos

```python
def can_continue(self) -> Tuple[bool, Optional[str]]:
    """Verifica si se pueden ejecutar más iteraciones."""
    
    if budget.iterations_used >= budget.limits.max_iterations:
        return False, "max_iterations"
    
    if budget.tool_calls_used >= budget.limits.max_tool_calls:
        return False, "max_tool_calls"
    
    if budget.context_tokens_used >= budget.limits.max_context_tokens:
        return False, "max_context_tokens"
    
    elapsed_ms = (time.time() - budget.start_time) * 1000
    if elapsed_ms >= budget.limits.max_wall_time_ms:
        return False, "max_wall_time_ms"
    
    return True, None

def apply_tool_result(self, tool: Tool, result: ToolResult):
    """Muta estado basado en resultado de ejecución."""
    
    if tool == "query_materials":
        for material in result.payload["materials"]:
            self.materials_found.append(
                MaterialRecord(
                    material_id=material["material_id"],
                    formula=material["formula"],
                    properties={...}
                )
            )
        self.budget.context_tokens_used += len(result.payload["materials"]) * 50

    elif tool == "search_documents":
        for doc in result.payload["documents"]:
            self.documents.append(DocumentRecord(...))
        self.budget.context_tokens_used += len(result.payload["documents"]) * 75

    # ... (idem para otras herramientas)
    
    self.budget.tool_calls_used += 1
```

---

## 5. Catálogo Técnico Detallado de Herramientas

### 5.1 query_materials_database

**Estado:** ✅ Producción | **Archivo:** `query_materials/` | **Costo:** 100-150pts | **Tiempo:** 150-3000ms

#### 5.1.1 Contrato de Entrada (Input Schema)

```json
{
  "type": "object",
  "properties": {
    "material_id": {"type": "string", "pattern": "^mp-\\d+$"},
    "formula": {"type": "string", "minLength": 1},
    "chemical_system": {"type": "string", "minLength": 1},
    "filters": {
      "type": "object",
      "properties": {
        "band_gap": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "number"}},
        "density": {"type": "array", "items": {"type": "number"}},
        "energy_above_hull": {"type": "array", "items": {"type": "number"}},
        "formation_energy": {"type": "array", "items": {"type": "number"}},
        "volume": {"type": "array", "items": {"type": "number"}},
        "is_stable": {"type": "boolean"},
        "is_metal": {"type": "boolean"}
      }
    },
    "ranking": {
      "type": "object",
      "properties": {
        "weights": {
          "type": "object",
          "properties": {
            "stability": {"type": "number"},
            "band_gap": {"type": "number"},
            "density": {"type": "number"},
            "energy_above_hull": {"type": "number"},
            "formation_energy": {"type": "number"},
            "volume": {"type": "number"}
          },
          "minProperties": 1
        },
        "objective": {"type": "object"}
      },
      "required": ["weights"]
    },
    "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5}
  },
  "oneOf": [
    {"required": ["material_id"]},
    {"required": ["formula"]},
    {"required": ["chemical_system"]}
  ]
}
```

**Restricciones:**
- Uno de `material_id`, `formula`, `chemical_system` REQUERIDO
- `ranking.weights` DEBEN sumar exactamente 1.0
- Rangos `[min, max]` son inclusivos ambos lados

#### 5.1.2 Contrato de Salida (Output Schema)

```json
{
  "type": "object",
  "properties": {
    "materials": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "material_id": {"type": "string"},
          "formula": {"type": "string"},
          "band_gap": {"type": "number"},
          "density": {"type": "number"},
          "is_stable": {"type": "boolean"},
          "is_metal": {"type": "boolean"},
          "energy_above_hull": {"type": "number"},
          "formation_energy": {"type": "number"},
          "volume": {"type": "number"}
        },
        "required": ["material_id", "formula", "band_gap", "density", "is_stable", "is_metal", "energy_above_hull", "formation_energy", "volume"]
      }
    },
    "count": {"type": "integer", "minimum": 0}
  },
  "required": ["materials", "count"]
}
```

**Ejemplo:**
```json
{
  "materials": [
    {
      "material_id": "mp-149",
      "formula": "Si",
      "band_gap": 1.166,
      "density": 2.328,
      "is_stable": true,
      "is_metal": false,
      "energy_above_hull": 0.0,
      "formation_energy": 0.0,
      "volume": 40.888
    }
  ],
  "count": 1
}
```

#### 5.1.3 Flujo de Ejecución

```
1. Inicialización cliente MP (lazy)
2. Construcción QueryRequest (mode: material_id|formula|chemical_system)
3. Consulta MP API (mpr.materials.summary.search)
4. Normalización documentos (validar tipos, descartar None)
5. Aplicación de filtros (rango + booleano)
6. Ranking si ranking_config presente:
   ├─ Calcular bounds [min, max] por propiedad
   ├─ Normalizar valores: (x - x_min) / (x_max - x_min)
   ├─ Calcular componentes por propiedad
   ├─ score = Σ(weight[i] × component[i])
   └─ Ordenar descendente
7. Truncar a limit & retornar

Complejidad: O(n log n) por sort
Tiempo típico: 150-3000ms (dominado por API)
```

#### 5.1.4 Lógica de Ranking Detallada

**Normalización Min-Max:**
```
normalized(x) = (x - x_min) / (x_max - x_min)
Casos especiales:
├─ Si x_min == x_max → normalizado = 0.5 para todos
└─ Si solo 1 material → todos los bounds = 0.5
```

**Componentes de Scoring:**

| Propiedad | Minimizar? | Fórmula | Lógica |
|---|---|---|---|
| stability | Sí | `-energy_above_hull` | Penaliza si inestable |
| energy_above_hull | Sí | `1.0 - normalized_value` | Busca 0 (estable) |
| formation_energy | Sí | `1.0 - normalized_value` | Busca negativo (favorable) |
| band_gap | No | `normalized_value` | Maximiza |
| density | No | `normalized_value` | Maximiza |
| volume | No | `normalized_value` | Maximiza |
| con objetivo | - | `-\|normalized - normalized_target\|` | Penaliza distancia |

**Ejemplo Numérico:**

Escenario: 3 Fe2O3, objetivo band_gap ≈ 2.0 eV
```
Input ranking: {stability: 0.4, band_gap: 0.6}

Materiales:
├─ Fe2O3_A: band_gap=2.2, energy=0.05
├─ Fe2O3_B: band_gap=1.8, energy=0.01
└─ Fe2O3_C: band_gap=null, energy=0.10

Normalización:
├─ band_gap_norm: [1.8, 2.2] → span=0.4
└─ energy_norm: [0.01, 0.10] → span=0.09
└─ target_norm: 2.0 → (2.0-1.8)/0.4 = 0.5

Scoring:
├─ Fe2O3_A:
│  ├─ stab_comp = -0.05
│  ├─ gap_comp = -|1.0 - 0.5| = -0.5
│  └─ score_A = 0.4×(-0.05) + 0.6×(-0.5) = -0.32
│
├─ Fe2O3_B:
│  ├─ stab_comp = -0.01
│  ├─ gap_comp = -|0.0 - 0.5| = -0.5
│  └─ score_B = 0.4×(-0.01) + 0.6×(-0.5) = -0.304 ✓ BEST
│
└─ Fe2O3_C:
   └─ score_C = -1e9 (penalidad null)

Orden final: B (-0.304), A (-0.32), C (null)
```

#### 5.1.5 Manejo de Errores

| Error | Código | Acción |
|---|---|---|
| Material ID ausente + formula ausente + chemsys ausente | VALIDATION_ERROR | Retornar error |
| MP_API_KEY no configurada | API_ERROR | Retornar error |
| Fallo conexión api.materialsproject.org | API_ERROR | Retornar error (evaluador decide retry) |
| Pesos no suman 1.0 | VALIDATION_ERROR | Retornar error |
| Respuesta API malformada | UNEXPECTED_ERROR | Captura, loguea, retorna error |

**Ningún reintento automático.** Evaluador decide si reintentar basado en error_code.

#### 5.1.6 Costo Computacional

```
Complejidad: O(n log n)
Puntos en policy: 100-150
Tiempo esperado: 150-3000ms (promedio ~500ms)
  ├─ API query: ~100-500ms
  ├─ Normalización: ~1-5ms
  ├─ Ranking: ~1-3ms
  └─ Overhead: ~10-20ms

Contexto generado: ~50 tokens/material

Wall time SLA: <2 segundos (con network latency)
```

---

### 5.2 search_scientific_documents

**Estado:** ✅ Producción | **Archivo:** `search_documents.py` | **Costo:** 250-400pts | **Tiempo:** 600-4000ms

#### 5.2.1 Contrato de Entrada

```json
{
  "properties": {
    "query": {"type": "string", "minLength": 3},
    "material_focus": {"type": "string"},
    "max_results": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10}
  },
  "required": ["query"],
  "additionalProperties": false
}
```

#### 5.2.2 Contrato de Salida

```json
{
  "documents": [{
    "doi": "string",
    "title": "string",
    "abstract": "string",
    "authors": ["array"],
    "publication_date": "YYYY-MM-DD",
    "citations": "int",
    "provider": "semantic_scholar|crossref|arxiv",
    "url": "string"
  }],
  "count": "int"
}
```

#### 5.2.3 Flujo de Ejecución

```
1. Validación query (minLength ≥ 3)
2. Tokenización y limpieza (minúsculas, stopwords)
3. Búsqueda paralela en 3 proveedores:
   ├─ SemanticScholar: mpr.paper.SearchResults(query, fields=[...])
   ├─ Crossref: GET /v1/works?query={query}
   └─ arXiv: GET /api/query?search_query=all:{query}
4. Normalización documentos crudo
5. Deduplicación multi-nivel:
   ├─ Nivel 1: Agrupar por DOI exacto
   ├─ Nivel 2: Nombre de título normalizado (fuzzy hash)
   └─ Nivel 3: Merge por prio SS > Crossref > arXiv
6. Vectorización híbrida:
   ├─ TF-IDF: Siempre (embeddings_client.vectorize_tfidf)
   ├─ Embeddings: Intento (embeddings_client.embed) → fallback graceful
   └─ Preparar corpus
7. Ranking ponderado:
   ├─ score = 0.6×embed_sim + 0.2×tfidf + 0.1×cites + 0.1×recency
   └─ Ordenar descendente
8. Filtro por material_focus si especificado
9. Truncar a max_results & retornar

Tiempo: 600-4000ms (dominado por 3 APIs paralelos)
```

#### 5.2.4 Deduplicación Inteligente

**Nivel 1: DOI Exacto**
```
Si documento A y B comparten DOI → agrupar
```

**Nivel 2: Título Fuzzy**
```
hash(normalize(title_A)) == hash(normalize(title_B))
  donde normalize = lowercase + remove_punctuation + tokens
  
Si collision → agrupar
```

**Nivel 3: Merge Multi-Proveedor**
```
Para cada grupo de duplicados:
  Retener: Información de proveedor con mayor prioridad
  Prioridad: SemanticScholar > Crossref > arXiv
  
  Merge de URLs: concatenar todas las source URLs
  Merge de autores: unión sin duplicados
```

#### 5.2.5 Ranking Híbrido

**Componentes:** (weights normalizados a suma=1.0)

| Componente | Peso | Rango | Fórmula |
|---|---|---|---|
| Embeddings | 0.60 | [0, 1] | cosine_similarity(query_embed, doc_embed) |
| TF-IDF | 0.20 | [0, 1] | CustomVectorizer.similarity_score |
| Citations | 0.10 | [0, 1] | min(citation_count / 100, 1.0) |
| Recency | 0.10 | [0, 1] | 1.0 - min(years_ago / 30, 1.0) |

**Score Final:**
```
score = 0.6×embed_sim + 0.2×tfidf_score + 0.1×norm_citations + 0.1×norm_recency

Rango final: [0, 1]
```

**Ejemplo:**
```
Doc A: "High-throughput screening band gap" (2023)
├─ Embeddings: 0.85 (alta similitud semántica)
├─ TF-IDF: 0.72 (contiene keywords)
├─ Citations: 0.42 (42 citas → 42/100 = 0.42)
├─ Recency: 1.0 (año 2023 completo)
└─ score = 0.6×0.85 + 0.2×0.72 + 0.1×0.42 + 0.1×1.0 = 0.762

Doc B: "Semiconductors" (2010)
├─ Embeddings: 0.45 (baja similitud)
├─ TF-IDF: 0.55 (keywords débil)
├─ Citations: 1.0 (100+ citas → cap a 1.0)
├─ Recency: 0.4 (13 años atrás → 1 - min(13/30) = 0.4)
└─ score = 0.6×0.45 + 0.2×0.55 + 0.1×1.0 + 0.1×0.4 = 0.495

Ranking: Doc A (0.762) > Doc B (0.495) ✓
```

#### 5.2.6 Fallback Graceful

**Si embeddings_client falla:**
```python
try:
    embeddings = embedding_client.embed(query, documents)
    rank_vectors = embeddings
except Exception:
    # Fallback: usa solo TF-IDF
    score = 0.0 × embeddings + 1.0 × tfidf + 0.0 × cites + 0.0 × recency
    # (redistribución de pesos, mantiene ranking)
```

**Si un proveedor falla:**
```
├─ Continuar con otros 2 proveedores
└─ Si todos fallan → stop_reason="PROVIDER_FAILURE"
```

**Si JSON parsing falla:**
```
├─ Loguea excepción
└─ Descarta documento problemático, continua
```

#### 5.2.7 Costo Computacional

```
Complejidad: O(n²) aproximadamente (por similitud pairwise en embedding)
Puntos: 250-400
Tiempo esperado: 600-4000ms (promedio ~1500ms)
  ├─ arXiv API: ~150-400ms
  ├─ SemanticScholar API: ~200-500ms
  ├─ Crossref API: ~100-300ms (parallelizado)
  ├─ Deduplicación: ~10-20ms
  ├─ Embeddings: ~200-800ms (si disponible)
  ├─ Ranking: ~50-100ms
  └─ Overhead: ~20-50ms

Contexto generado: ~75 tokens/documento

Wall time SLA: <5 segundos
```

---

### 5.3 validate_material_constraints

**Estado:** ✅ Producción | **Precondiciones:** state.materials_found + state.constraints | **Costo:** 50pts | **Tiempo:** 20-50ms

#### 5.3.1 Contrato de Entrada

```json
{
  "constraints": [{
    "property": {"type": "string"},
    "operator": {"enum": [">=", "<=", "==", ">", "<", "!="]},
    "value": {"type": ["number", "string", "boolean"]}
  }],
  "agent_state": {"type": "object"}
}
```

#### 5.3.2 Contrato de Salida

```json
{
  "valid": {"type": "boolean"},
  "materials_satisfying_constraints": {"type": "array", "items": {"type": "string"}},
  "materials_failing_constraints": {"type": "array", "items": {"type": "string"}},
  "summary": {
    "total_materials_checked": {"type": "integer"},
    "total_satisfying": {"type": "integer"},
    "total_failing": {"type": "integer"},
    "constraints_checked": {"type": "integer"}
  }
}
```

#### 5.3.3 Flujo de Ejecución

```
1. Validación de parámetros (agent_state presente)
2. Validación de state (materials_found no vacío)
3. Para cada material en state:
   ├─ Para cada constraint:
   │  ├─ Extraer property del material (búsqueda multi-nivel)
   │  ├─ Aplicar operador (>=, <=, ==, etc.)
   │  └─ Si falla 1 constraint → marcar como failing
   │
   └─ Si todas las constraints ok → marcar como satisfying
4. Compilar listas y resumen
5. Retornar resultado

Complejidad: O(m × c) donde m=materiales, c=constraints
Tiempo: ~20-50ms (completamente local)
```

#### 5.3.4 Operadores Soportados

| Operador | Semántica | Ejemplo |
|---|---|---|
| `>=` | mayor o igual | `band_gap >= 1.5` |
| `<=` | menor o igual | `density <= 3.0` |
| `==` | igual exacto | `is_stable == true` |
| `>` | estrictamente mayor | `energy_above_hull > 0.05` |
| `<` | estrictamente menor | `volume < 50` |
| `!=` | no igual | `is_metal != true` |

#### 5.3.5 Resolución Flexible de Valores

```python
def resolve_property_value(material, property_name):
    # Búsqueda multi-nivel:
    
    # Nivel 1: properties dict
    if property_name in material.properties:
        return material.properties[property_name]
    
    # Nivel 2: atributos diréctos
    if hasattr(material, property_name):
        return getattr(material, property_name)
    
    # Nivel 3: None (property missing)
    return None

def evaluate_constraint(value, operator, target):
    if value is None:
        return False  # Falla si property missing
    
    if operator == ">=":
        return value >= target
    elif operator == "<=":
        return value <= target
    # ... etc
```

#### 5.3.6 Costo Computacional

```
Complejidad: O(m × c)
Puntos: 50 (bajo)
Tiempo: 20-50ms (completamente local, sin I/O)
Contexto: ~5 tokens/resultado

100% predecible, determinístico
```

---

### 5.4 extract_document_insights

**Estado:** ✅ Producción | **Precondiciones:** state.documents | **Costo:** 500pts | **Tiempo:** 500-3000ms

#### 5.4.1 Contrato de Entrada

```json
{
  "documents": [{
    "title": {"type": "string"},
    "abstract": {"type": "string"},
    "doi": {"type": "string"}
  }],
  "focus_area": {
    "type": "string",
    "enum": ["material_properties", "synthesis", "characterization", "applications"],
    "default": "material_properties"
  }
}
```

#### 5.4.2 Contrato de Salida

```json
{
  "insights": [{
    "document_title": {"type": "string"},
    "extracted_insights": [{
      "insight": {"type": "string"},
      "relevance": {"type": "number", "minimum": 0, "maximum": 1}
    }],
    "fallback_used": {"type": "boolean"}
  }],
  "count": {"type": "integer"}
}
```

#### 5.4.3 Flujo de Ejecución

```
1. Preparación de prompt (template + focus area)
2. Por cada documento:
   ├─ Construir mensaje: título + abstract
   └─ Agregar al historial
3. Llamada a LLM remoto:
   ├─ POST {AGENTS_URL}/v1/completions
   ├─ temperature=0.1 (determinismo bajo)
   ├─ max_tokens=300 (output bounded)
   └─ timeout=10s
4. Parsing JSON robusto:
   ├─ Intento 1: json.loads(response)
   ├─ Intento 2: Extraer substring entre { y }
   ├─ Si éxito: validar schema
   └─ Si falla: usar fallback
5. Por cada documento procesado:
   ├─ Si LLM exitoso: agregar insights reales
   └─ Si LLM falló: usar fallback genérico + marcar fallback_used=true
6. Compilar resultado & retornar

Tiempo: 500-3000ms (dominado por LLM inference)
```

#### 5.4.4 Fallback Graceful

**Si LLM falla o JSON parsing falla:**

```python
FALLBACK_INSIGHTS = [
    {"insight": "Material properties mentioned", "relevance": 0.78},
    {"insight": "Synthesis methodology described", "relevance": 0.72},
    {"insight": "Characterization data included", "relevance": 0.68},
    {"insight": "Performance metrics discussed", "relevance": 0.65}
]

# Resultado mantenido siempre válido, nunca rompe flujo
```

#### 5.4.5 Prompt Template

```
SYSTEM:
"Eres un experto en extracción de información científica.
 Tu tarea es extraer insights clave de documentos científicos
 sobre {focus_area}.
 
 Retorna un JSON con estructura:
 {'insights': [{'insight': 'texto breve', 'relevance': float}]}"

USER:
"Documento: {title}
 Resumen: {abstract}
 
 Extrae insights sobre {focus_area}."
```

#### 5.4.6 Características Especiales

- **Temperature baja (0.1):** Para determinismo (vs 0.7 típico)
- **JSON parsing resiliente:** 2 intentos antes de fallback
- **Fallback sintético:** Garantiza salida siempre válida
- **Sin requemutación estado:** Herramienta es pura

#### 5.4.7 Costo Computacional

```
Tiempo: 500-3000ms (promedio ~1200ms)
Puntos: 500 (alto, LLM-based)
Contexto: ~30 tokens/insight

SLA: <5 segundos
```

---

### 5.5 compare_materials (STUB - NO PRODUCCIÓN)

**Estado:** 🟡 STUB | **Completitud:** 5% | **Acción:** Implementar

#### 5.5.1 Especificación Deseada

```json
{
  "input": {
    "material_ids": ["mp-149", "mp-286"],
    "properties_to_compare": ["band_gap", "density"]
  },
  "output": {
    "comparison": [{
      "property": "band_gap",
      "materials": [
        {"material_id": "mp-149", "value": 1.166, "rank": 1},
        {"material_id": "mp-286", "value": 0.0, "rank": 2}
      ],
      "best_for": "mp-149"
    }],
    "overall_best": "mp-149"
  }
}
```

#### 5.5.2 Cambios Requeridos

1. Lookup real de materiales en `state.materials_found`
2. Validación que material_ids existen
3. Extracción de propiedades solicitadas
4. Scoring y ranking por propiedad
5. Identificación de "best_for" por propiedad y overall
6. Serialización a JSON

---

### 5.6 generate_crystal_structure (STUB - NO PRODUCCIÓN)

**Estado:** 🟡 STUB | **Completitud:** 5% | **Acción:** Implementar

#### 5.6.1 Especificación Deseada

```json
{
  "input": {
    "material_id": "mp-149",
    "format": "cif"  // cif | poscar | json
  },
  "output": {
    "structure_data": "structure in requested format",
    "lattice_parameters": {
      "a": 5.431,
      "b": 5.431,
      "c": 5.431,
      "alpha": 90,
      "beta": 90,
      "gamma": 90
    },
    "space_group": "Fd-3m",
    "point_group": "m-3m"
  }
}
```

#### 5.6.2 Implementación Requerida

```python
from mp_api.client import MPRester
from pymatgen.io.cif import CifWriter
from pymatgen.io.poscar import Poscar

def execute(material_id, format):
    # 1. Retrieval structure
    with MPRester(MP_API_KEY) as mpr:
        structure = mpr.get_structure_by_material_id(material_id)
    
    # 2. Serialization
    if format == "cif":
        writer = CifWriter(structure)
        return writer.get_string()
    elif format == "poscar":
        poscar = Poscar(structure)
        return str(poscar)
    elif format == "json":
        return structure.to_json()
    
    # 3. Extract lattice parameters
    lattice_params = {
        "a": structure.lattice.a,
        "b": structure.lattice.b,
        "c": structure.lattice.c,
        "alpha": structure.lattice.alpha,
        "beta": structure.lattice.beta,
        "gamma": structure.lattice.gamma
    }
    
    return {
        "structure_data": serialized_structure,
        "lattice_parameters": lattice_params,
        "space_group": structure.get_space_group_info()[0],
        "point_group": structure.get_point_group_symbol()
    }
```

---

## 6. ToolRegistry (Detalle Completo)

### 6.1 Validación de Esquemas

```python
class ToolRegistry:
    
    def validate_input(self, tool: Tool, arguments: Dict) -> Tuple[bool, Optional[str]]:
        """Valida input contra JSON schema de la herramienta."""
        
        schema = tool.input_schema
        try:
            jsonschema.validate(arguments, schema)
            return True, None
        except jsonschema.ValidationError as exc:
            return False, str(exc)
    
    def validate_output(self, tool: Tool, result: ToolResult) -> Tuple[bool, Optional[str]]:
        """Valida output contra JSON schema de la herramienta."""
        
        schema = tool.output_schema
        try:
            jsonschema.validate(result.payload, schema)
            return True, None
        except jsonschema.ValidationError as exc:
            return False, str(exc)
```

### 6.2 Precondiciones

```python
def can_run(self, tool: Tool, state: AgentState) -> bool:
    """Verifica si herramienta puede ejecutarse."""
    
    # Por herramienta:
    preconditions = {
        "query_materials": lambda s: True,  # Siempre
        
        "validate_constraints": lambda s: (
            len(s.materials_found) > 0 and
            len(s.constraints) > 0
        ),
        
        "compare_materials": lambda s: len(s.materials_found) >= 2,
        
        "extract_insights": lambda s: len(s.documents) > 0,
        
        "search_documents": lambda s: True,  # Siempre
        
        "generate_structure": lambda s: len(s.materials_found) > 0
    }
    
    return preconditions.get(tool.name, lambda s: False)(state)
```

---

## 7. Endpoints HTTP Internos

### 7.1 `POST /v3/completions`

**Request:**
```json
{
  "query": "Find materials with band gap > 2.0 eV",
  "stream": false,
  "temperature": 0.2,
  "max_tokens_for_response": 512,
  "max_iterations": 10,
  "max_tool_calls": 15,
  "max_context_tokens": 4096,
  "max_wall_time_ms": 60000
}
```

**Response (modo normal):**
```json
{
  "id": "req-abc123",
  "object": "text_completion",
  "choices": [{
    "text": "I found several materials with band gap > 2.0 eV..."
  }],
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 200,
    "total_tokens": 350,
    "context_tokens": 2100
  },
  "metadata": {
    "iterations_count": 3,
    "tool_calls_count": 3,
    "context_tokens_used": 2100,
    "stop_reason": "sufficient_evidence",
    "elapsed_ms": 3500,
    "materials_found": 5,
    "documents_found": 12,
    "insights_found": 8,
    "evaluator_feedback": [
      {"sufficient": false, "confidence": 0.45, "missing_information": ["comparison"], ...},
      {"sufficient": false, "confidence": 0.65, "missing_information": ["synthesis"], ...},
      {"sufficient": true, "confidence": 0.88, "missing_information": [], ...}
    ]
  }
}
```

**Response (modo SSE):**
```
event: start
data: {"request_id": "req-abc123", "query": "Find materials..."}

event: loop_done
data: {"request_id": "req-abc123", "stop_reason": "sufficient_evidence", "iterations": 3, "tool_calls": 3}

event: final
data: {"request_id": "req-abc123", "response": "I found several materials..."}
```

### 7.2 Headers de SSE

```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

---

## 8. Persistencia de Trazas

Cada request genera un archivo JSON en `AGENT_TRACE_DIR`:

**Nombre:** `{request_id}.json`

**Estructura:**
```json
{
  "request": {
    "id": "req-abc123",
    "query": "Find materials...",
    "timestamp": "2024-03-24T10:15:30Z"
  },
  "state_final": {
    "materials_found": [...],
    "documents": [...],
    "extracted_insights": [...],
    "constraints": [...],
    "budget": {...}
  },
  "tool_execution_history": [
    {
      "iteration": 1,
      "tool": "query_materials_database",
      "input": {...},
      "output": {...},
      "status": "success",
      "elapsed_ms": 450
    },
    ...
  ],
  "evaluator_feedback_history": [
    {"sufficient": false, "confidence": 0.45, ...},
    ...
  ],
  "response": "I found several materials...",
  "metadata": {
    "stop_reason": "sufficient_evidence",
    "total_elapsed_ms": 3500,
    "iterations": 3,
    "tool_calls": 3
  }
}
```

---

## 9. Variables de Entorno (Detalle)

| Variable | Por Herramienta/Componente | Requerido | Default | Descripción |
|---|---|---|---|---|
| `MP_API_KEY` | query_materials | ✅ Sí | - | API key para Materials Project API |
| `SEMANTIC_SCHOLAR_API_KEY` | search_documents | ❌ Opcional | - | API key eleva rate limits Semantic Scholar |
| `CROSSREF_EMAIL` | search_documents | ✅ Sí | - | Email para Crossref API (User-Agent) |
| `AGENTS_URL` | extract_insights + evaluator | ✅ Sí | http://agents:8003 | URL del servicio de LLM (Ollama/agents) |
| `AGENT_INSIGHTS_MODEL` | extract_insights | ✅ Sí | Qwen2.5-7B-Instruct-1M | Modelo para extracción de insights |
| `AGENT_EVALUATOR_MODEL` | evaluator | ✅ Sí | Qwen2.5-7B-Instruct-1M | Modelo para evaluación de evidencia |
| `AGENTS_SERVICE_URL` | search_documents (fallback) | ❌ Opcional | http://agents:8000 | URL alternativa para búsqueda (embeddings) |
| `CORS_ALLOW_ORIGINS` | app.py | ✅ Sí | http://localhost:3000 | Orígenes permitidos para CORS |
| `AGENT_TRACE_DIR` | persistencia | ✅ Sí | agent_core/data/traces | Directorio para persistencia de trazas |

---

## 10. Tabla Comparativa de Herramientas

| Herramienta | Estado | Input | Precond. | Tiempo (ms) | Costo (pts) | APIs | Determinístico |
|---|---|---|---|---|---|---|---|
| query_materials | ✅ Prod | material_id\|formula | Ninguno | 150-3000 | 100-150 | MP | 100% |
| search_documents | ✅ Prod | query | Ninguno | 600-4000 | 250-400 | SS,CF,arXiv | 99% |
| validate_constraints | ✅ Prod | constraints | materials_found | 20-50 | 50 | Ninguno | 100% |
| extract_insights | ✅ Prod | documents[] | documents | 500-3000 | 500 | LLM | 90% |
| compare_materials | 🟡 STUB | material_ids[] | >=2 mats | <5 | 200 | Ninguno | - |
| generate_structure | 🟡 STUB | material_id | >=1 mat | < 1 | 400 | MP | - |

---

Este es el **documento de referencia técnica completa**. Todos los detalles de implementación, fórmulas, esquemas y flujos están aquí.
