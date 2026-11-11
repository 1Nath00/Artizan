# Guía de Mejoras del Sistema RAG - Implementación

## 📋 Resumen Ejecutivo

Se han implementado mejoras integrales en el sistema RAG para:
- ✅ Mejorar precision/recall de recuperación
- ✅ Reducir duplicación de chunks
- ✅ Generar respuestas más fieles y completas
- ✅ Citar adecuadamente todas las fuentes
- ✅ Medir y optimizar latencia
- ✅ Proporcionar evaluación integral

---

## 🗂️ Archivos Nuevos Creados

### Módulos de Mejora

1. **`app/models/rag/retrieval_optimizations.py`**
   - Deduplicación de chunks similares
   - Maximal Marginal Relevance (MMR)
   - Análisis de recuperación
   - Funciones de similitud

2. **`app/models/rag/generation_improvements.py`**
   - Prompt mejorado y estructurado
   - Validación de citas
   - Detección de alucinaciones
   - Estadísticas de respuesta

3. **`app/models/rag/comprehensive_evaluation.py`**
   - Evaluación integral del RAG
   - Reporte automatizado
   - Métricas cruzadas (retrieval + generation)

### Scripts de Diagnóstico y Prueba

4. **`test_rag_improvements.py`**
   - Pruebas de valores K (1, 3, 5, 8, 10, 12, 15, 20)
   - Análisis de deduplicación
   - Pruebas de calidad de generación
   - CSV de resultados

5. **`diagnostico_rag_mejorado.py`**
   - Diagnóstico integral con los mismos datos
   - Reporte comparativo automático
   - Exportación a JSON y CSV
   - Comparación antes/después

6. **`analizar_chunking.py`**
   - Análisis de configuración de chunking actual
   - Estadísticas de tamaño de chunks
   - Recomendaciones de optimización
   - Configuraciones alternativas a probar

### Documentación

7. **`RAG_IMPROVEMENT_PLAN.md`**
   - Plan detallado de mejoras
   - Restricciones y principios
   - Métricas de éxito

---

## 🚀 Cómo Usar las Mejoras

### Paso 1: Analizar Chunking Actual

```bash
python analizar_chunking.py
```

**Salida esperada:**
- Estadísticas de chunks actuales
- Distribución de tamaños
- Recomendaciones de optimización

### Paso 2: Ejecutar Pruebas de K

```bash
python test_rag_improvements.py
```

**Salida esperada:**
- Resultados de retrieval para K=[1,3,5,8,10,12,15,20]
- Análisis de deduplicación
- Pruebas de generación
- CSV: `test_k_results.csv`

### Paso 3: Ejecutar Diagnóstico Mejorado

```bash
python diagnostico_rag_mejorado.py
```

**Salida esperada:**
- Evaluación integral para todas las preguntas de prueba
- JSONL: `diagnostico_mejorado.jsonl`
- CSV: `diagnostico_comparacion.csv`
- Reporte de comparación con línea base
- Métricas detalladas por pregunta

---

## 📊 Métricas Clave Mejoradas

### 1. Recuperación (Retrieval)

**Nueva funcionalidad:**
```python
# Con deduplicación automática
hits = service.retrieve(question, k=10, use_deduplication=True)

# Análisis detallado
result = service.analyze_retrieval(question, k=10)
# Retorna: cantidad_chunks, chunks_unicos, tasa_duplicacion, 
#          promedio_longitud, documentos_unicos, distancia_promedio
```

**Métricas medidas:**
- `hits_count`: Chunks recuperados
- `unique_documents`: Documentos únicos
- `avg_distance`: Similitud promedio
- `duplicate_rate`: Porcentaje de duplicados
- `chunk_coverage`: Fragmentos utilizados (%)

### 2. Generación (Generation)

**Mejoras:**
- Prompt más estructurado y riguroso
- Contexto agrupado por documento
- Instrucciones explícitas para citas
- Detección de abstención

**Métricas medidas:**
- `word_count`: Palabras en respuesta
- `sentence_count`: Número de oraciones
- `avg_sentence_length`: Promedio por oración

### 3. Citas (Citations)

**Validación automática:**
```python
from app.models.rag.generation_improvements import validate_citations

citations = validate_citations(answer, num_fragments=10)
# Retorna: total_citations, unique_citations, valid_citations,
#          invalid_citations, invalid_ids, missing_fragments, coverage
```

**Métricas medidas:**
- `total_citations`: Citas totales (incluyendo repetidas)
- `unique_citations`: Fragmentos únicos citados
- `valid_citations`: Citas dentro del rango válido
- `invalid_citations`: Citas fuera de rango
- `coverage`: % de fragmentos utilizados

### 4. Latencia

**Desglose de tiempos:**
```python
result = service.ask(question, k=10)
# Retorna: latency_breakdown = {
#   "retrieval_ms": tiempo de recuperación,
#   "llm_ms": tiempo del LLM
# }
```

---

## 🔄 Cambios en Código Existente

### `app/models/rag/service.py`

**1. SYSTEM_PROMPT mejorado**
```python
# Antes: Instrucciones básicas
# Después: Instrucciones más rigurosas con énfasis en:
#  - Uso exclusivo de contexto
#  - Citas obligatorias [n]
#  - Detección de información insuficiente
#  - No invención de datos
```

**2. Función `build_messages()` mejorada**
```python
# Antes: Lista simple de fragmentos
# Después: Fragmentos agrupados por documento
#  - Mejor organización del contexto
#  - Número de fragmento + documento claro
```

**3. Función `retrieve()` mejorada**
```python
# Antes: Sin deduplicación
# Después: Con opciones de deduplicación
retrieve(question, k, use_deduplication=True, dedup_threshold=0.7)
```

**4. Función `ask()` mejorada**
```python
# Antes: Solo latencia total
# Después: Desglose de latencia
# Retorna: latency_breakdown = {retrieval_ms, llm_ms}
```

**5. Funciones nuevas**
```python
retrieve_multiple_k(question, k_values)  # Pruebas de K
analyze_retrieval(question, k)           # Análisis detallado
```

---

## 🎯 Optimizaciones Implementadas

### A. Deduplicación de Chunks

**Problema:** Chunks muy similares aparecen en top-K
**Solución:** Similitud textual con umbral configurable
**Uso:**
```python
from app.models.rag.retrieval_optimizations import deduplicate_hits

hits = [...] # 10 chunks recuperados
dedup = deduplicate_hits(hits, similarity_threshold=0.7)  # 7-8 chunks únicos
```

### B. Análisis de Recuperación

**Problema:** Sin visibilidad de duplicación
**Solución:** Estadísticas detalladas de chunks
**Uso:**
```python
from app.models.rag.retrieval_optimizations import analyze_chunks

stats = analyze_chunks(hits)
print(stats["tasa_duplicacion"])  # e.g., 20.5%
```

### C. Validación de Citas

**Problema:** Citas sin validación, números inválidos
**Solución:** Extracción y validación de [1], [2], etc.
**Uso:**
```python
from app.models.rag.generation_improvements import validate_citations

stats = validate_citations(answer, num_fragments=10)
if stats["invalid_citations"]:
    print(f"Citas inválidas: {stats['invalid_ids']}")
```

### D. Latencia Desglosada

**Problema:** Sin visibilidad de dónde se gasta el tiempo
**Solución:** Medición por componente
**Uso:**
```python
result = service.ask(question, k=10)
print(result["latency_breakdown"])  # {retrieval_ms: 150, llm_ms: 2500}
```

---

## 📈 Cómo Interpretar Resultados

### Prueba 1: `test_rag_improvements.py`

**CSV: `test_k_results.csv`**

| Columna | Significado |
|---------|------------|
| k | Número de fragmentos recuperados |
| hits_found | Cantidad real de chunks (puede ser < k) |
| unique_documents | Documentos únicos en resultados |
| avg_distance | Similitud promedio (0=disímil, 1=idéntico) |
| retrieval_time_ms | Tiempo de recuperación en milisegundos |

**Interpretación:**
- Si `avg_distance` decrece con K mayor → más ruido en recuperación
- Si `retrieval_time_ms` crece linealmente → escalable
- Si `unique_documents` es bajo → redundancia de documentos

### Prueba 2: `diagnostico_rag_mejorado.py`

**JSONL: `diagnostico_mejorado.jsonl`**
- Línea por pregunta con métricas completas
- Útil para análisis detallado
- Contiene: retrieval, generation, citations, latency, integrated

**CSV: `diagnostico_comparacion.csv`**
- Vista tabular agregada
- Fácil de comparar entre preguntas
- Columnas: topic, question, k, retrieval_*, gen_*, cites_*, latency_*

**Reporte de texto:**
- Resumen de promedios
- Análisis de problemas comunes
- Comparación con línea base

---

## 🧪 Casos de Prueba Incluidos

Todos los scripts usan las mismas preguntas que el diagnóstico original:

**Cubismo:**
1. ¿Qué es el cubismo?
2. Define el cubismo como movimiento artístico.
3. ¿Cuáles son las características del cubismo?
4. ¿Quiénes fundaron el cubismo y cuándo surgió?
5. ¿En qué consiste la representación cubista de los objetos?

**Barroco:**
1. ¿Qué es el barroco?
2. Define el arte barroco.
3. ¿Cuáles son las características del barroco?
4. ¿Cuándo surgió el barroco y qué lo caracteriza?
5. ¿Qué significa el término barroco?

---

## ⚙️ Configuración y Parámetros

### Variables de Entorno (`.env`)

```bash
# Chunking (optimizable)
RAG_CHUNK_SIZE=900           # Caracteres por chunk
RAG_CHUNK_OVERLAP=150        # Solapamiento entre chunks

# Recuperación
RAG_TOP_K=5                  # K por defecto (recomendado: 10)

# Generación
RAG_TEMPERATURE=0.2          # Determinismo (bajo=más determinista)
RAG_NUM_CTX=4096             # Contexto del LLM

# Embeddings
RAG_EMBEDDING_MODEL=intfloat/multilingual-e5-small

# LLM
RAG_LLM_MODEL=llama3.2
OLLAMA_HOST=http://localhost:11434
```

### Parámetros de Deduplicación

```python
# En retrieve()
deduplicate_hits(hits, similarity_threshold=0.7)
# Ajustar threshold según necesidad:
# - 0.5: muy agresivo (elimina muchos chunks)
# - 0.7: equilibrado (recomendado)
# - 0.9: muy conservador (elimina pocos)
```

---

## 🔍 Troubleshooting

### Problema: "No encuentro información suficiente"

**Causas:**
- K demasiado bajo → aumentar a 12-15
- Chunks no relevan → mejorar embeddings o chunking
- Pregunta fuera de alcance → validar documentos

**Solución:**
```python
# Ejecutar prueba de K
python test_rag_improvements.py

# Ver qué chunks se recuperan
result = service.retrieve_multiple_k(question, k_values=[5,10,15])
```

### Problema: Citas inválidas [15] cuando solo hay 10 fragmentos

**Causa:** LLM inventa números de cita
**Solución:** 
- Usar prompt mejorado (ya implementado)
- Validar citas automáticamente
- Verificar quality del modelo LLM

```python
from app.models.rag.generation_improvements import validate_citations
stats = validate_citations(answer, num_fragments=10)
if stats["invalid_citations"]:
    print(f"Citas inválidas: {stats['invalid_ids']}")
```

### Problema: Latencia muy alta (>20s)

**Análisis:**
```python
result = service.ask(question, k=10)
print(result["latency_breakdown"])
# Si llm_ms >> retrieval_ms → problema en LLM/modelo
# Si retrieval_ms alto → problema en base de datos
```

---

## 📝 Próximos Pasos Recomendados

### Corto Plazo (Inmediato)

1. ✅ Ejecutar `test_rag_improvements.py` 
   - Identificar mejor K
   - Medir impacto de deduplicación

2. ✅ Ejecutar `diagnostico_rag_mejorado.py`
   - Obtener línea base mejorada
   - Comparar con diagnóstico anterior

3. ✅ Ejecutar `analizar_chunking.py`
   - Evaluar configuración actual
   - Identificar mejoras de chunking

### Mediano Plazo (Próxima iteración)

4. Probar configuraciones alternativas de chunking
   - Cambiar `RAG_CHUNK_SIZE` y `RAG_CHUNK_OVERLAP`
   - Reindexar con `POST /models/rag/index`
   - Comparar resultados de recuperación

5. Implementar selección automática de K
   - Basada en complejidad de pregunta
   - Basada en cantidad de documentos

6. Considerar MMR (Maximal Marginal Relevance)
   - Ya está disponible en `retrieval_optimizations.py`
   - Agregar como opción configurable en `retrieve()`

### Largo Plazo (Mejoras Futuras)

7. Integrar Cross-Encoder reranker
   - Mejora adicional después de vector similarity
   - Mejora precision sin aumentar mucho latencia

8. Cacheo de embeddings
   - Precomputar embeddings de preguntas frecuentes
   - Reducir tiempo de embedding

9. Batch processing
   - Procesar múltiples preguntas en paralelo
   - Útil para evaluación

10. Fine-tuning de embeddings
    - Adaptar modelo a dominio específico (arte)
    - Requiere datos etiquetados

---

## 📚 Documentación de Referencia

- `RAG_IMPROVEMENT_PLAN.md`: Plan detallado de mejoras
- `app/models/rag/retrieval_optimizations.py`: Docstrings de funciones
- `app/models/rag/generation_improvements.py`: Docstrings de funciones
- `app/models/rag/comprehensive_evaluation.py`: Sistema de evaluación

---

## ✅ Checklist de Validación

- [ ] Scripts de prueba ejecutan sin errores
- [ ] `test_k_results.csv` se genera correctamente
- [ ] `diagnostico_mejorado.jsonl` tiene 10 preguntas
- [ ] `diagnostico_comparacion.csv` muestra todas las métricas
- [ ] Citas son válidas en respuestas
- [ ] Latencia se desglos adecuadamente
- [ ] Endpoint `/ask` sigue funcionando sin cambios
- [ ] Deduplicación reduce duplicados (>5%)
- [ ] Prompt mejorado se aplica correctamente
- [ ] No hay errores en imports de nuevos módulos
