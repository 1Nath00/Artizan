# Plan Integral de Mejora del Sistema RAG

## 1. ANÁLISIS DE LA ARQUITECTURA ACTUAL

### Componentes Clave
- **Modelo de embeddings**: `intfloat/multilingual-e5-small` (384-dimensional, optimizado para español)
- **Base de datos vectorial**: ChromaDB (con métrica cosine similarity)
- **Modelo LLM**: Ollama con `llama3.2` 
- **Estrategia de recuperación**: 
  - Búsqueda vectorial inicial (top k*4 candidatos)
  - Reranking híbrido con BM25/TF-IDF lexical (Reciprocal Rank Fusion)
  - Selección final de top-K

### Configuración Actual
- Chunk size: 900 caracteres
- Chunk overlap: 150 caracteres
- Top-K recuperado: 5 (RAG_TOP_K), pero K=10 mostró mejor F1
- Temperature: 0.2
- Num context: 4096 tokens

### Flujo RAG Actual
```
Pregunta → Embedding de query → Búsqueda vectorial (top k*4) 
→ Reranking BM25 → Top-K → Construcción contexto 
→ LLM (Ollama) → Respuesta → Evaluación
```

## 2. PROBLEMAS IDENTIFICADOS

### A. Retrieval (Recuperación)
1. **Precision baja (0.62)**: Muchos chunks irrelevantes en top-K
2. **Recall bajo (0.605)**: Se pierden fragmentos relevantes
3. **F1 limitado (0.556)**: Desbalance entre precision/recall
4. **K=10 vs K=5**: Cambio de parámetro mejora, pero:
   - Latencia aumenta
   - Riesgo de ruido en contexto
5. **Robustez variable (Jaccard 0.48-0.49)**: Mal manejo de paráfrasis
6. **Duplicación de chunks**: Chunks muy similares en misma respuesta
7. **Chunking potencial problema**: 
   - Tamaño 900 puede fragmentar conceptos largos
   - Overlap 150 puede no ser suficiente para contexto largo
   - Separación de títulos/subtítulos no optimizada

### B. Generation (Generación)
1. **Completitud subóptima (4/5)**: Omite información disponible
2. **Latencia alta (18.16s)**: Cuello de botella en la evaluación + LLM
3. **Alucinaciones posibles**: Aunque fidelidad=0.95, hay riesgo
4. **Prompt puede mejorar**: 
   - No instruye sobre citas locales
   - No fuerza exhaustividad
   - No gestiona bien la abstención

### C. Evaluación
1. **Métricas de retrieval y generation separadas**: No hay relación clara
2. **Sin reranking adicional después de recuperación vectorial**
3. **Sin MMR (Maximal Marginal Relevance)**: No diversifica resultados
4. **Sin deduplicación de chunks**: Información repetida

### D. Latencia
- 18.16s total (pregunta sobre cubismo)
- Sin desglose de tiempos individuales
- Probable culpable: evaluación LLM + generación

## 3. PLAN DE IMPLEMENTACIÓN (ETAPAS)

### Etapa 1: Análisis de Chunking y Embeddings
- [ ] Analizar chunks actuales en la DB
- [ ] Probar configuraciones alternativas:
  - Chunk size: 600, 800, 1000, 1200
  - Overlap: 100, 150, 200, 250
- [ ] Validar que embeddings están normalizados
- [ ] Verificar compatibilidad embedding/query

### Etapa 2: Optimización de Recuperación
- [ ] Implementar Maximal Marginal Relevance (MMR)
- [ ] Probar K alternativo (8, 10, 12, 15, 20)
- [ ] Agregar reranking adicional (Cross-Encoder o similar)
- [ ] Deduplicación de chunks con umbral de similaridad
- [ ] Métricas de recuperación detalladas

### Etapa 3: Mejora de Generación
- [ ] Revisar y mejorar SYSTEM_PROMPT
- [ ] Instrucciones para:
  - Citar todas las fuentes relevantes
  - Usar TODOS los fragmentos disponibles
  - Evitar alucinaciones
  - Abstenerse cuando sea necesario
- [ ] Validar que respuestas usan información del contexto

### Etapa 4: Sistema de Evaluación Integral
- [ ] Mantener métricas de retrieval (precision, recall, F1, Jaccard)
- [ ] Mantener métricas de generation (fidelidad, completitud, etc.)
- [ ] Agregar métricas cruzadas:
  - Coverage: ¿se usan todos los chunks recuperados?
  - Groundedness: ¿cada afirmación tiene evidencia?
  - Source validity: ¿las citas son correctas?

### Etapa 5: Optimización de Latencia
- [ ] Medir tiempos de cada componente
- [ ] Reducir contexto innecesario
- [ ] Optimizar calls al juez (cacheo, parallelización)
- [ ] Considerar batch processing
- [ ] Reutilizar embeddings

### Etapa 6: Validación y Comparación
- [ ] Ejecutar diagnóstico con los MISMOS datos
- [ ] Generar reporte de antes/después
- [ ] Validar que no se rompieron endpoints
- [ ] Pruebas de regresión

## 4. RESTRICCIONES Y PRINCIPIOS

✓ Mantener compatibilidad con FastAPI
✓ No romper endpoints actuales
✓ Reutilizar servicios, repositorios, modelos
✓ Parametrizar configuraciones
✓ Agregar pruebas unitarias
✓ No inventar resultados
✓ Comparar SIEMPRE antes y después
✓ No regenerar embeddings sin justificación

## 5. MÉTRICAS DE ÉXITO

| Métrica | Línea Base | Objetivo | Peso |
|---------|-----------|----------|------|
| Precision | 0.62 | 0.75+ | 20% |
| Recall | 0.605 | 0.72+ | 20% |
| F1 Score | 0.556 | 0.70+ | 20% |
| Fidelidad | 0.95 | 0.97+ | 15% |
| Completitud | 4/5 | 4.5/5 | 15% |
| Latencia | 18.16s | 12s | 10% |

## 6. DELIVERABLES ESPERADOS

1. Diagnóstico detallado de problemas
2. Código mejorado con cambios documentados
3. Nuevos tests de evaluación
4. Reporte comparativo antes/después
5. Configuración optimizada
6. Documentación de limitaciones y mejoras futuras
