# Guía de Mantenimiento del Índice RAG - Post-Resolución

## Estado Actual

✅ **Sistema RAG completamente restaurado y funcional**

- Índice: **4,709 chunks** indexados correctamente
- Cobertura: **100%** (22 de 22 documentos)
- Cubismo F1: **0.667** (antes: 0.222)
- Barroco F1: **0.638** (estable)

## Qué Pasó

El índice ChromaDB se corrompió/incompletó en un fallo anterior, indexando solo 2,000 chunks 
de 4,700+ disponibles. Cuando se agregaron más textos de cubismo, el índice corrupto colapsó 
completamente. La solución fue hacer un rebuild desde cero.

## Scripts Disponibles

### 1. Validación del Índice
```bash
python validate_rag_index.py
```
✅ Verifica que el índice esté completo y correcto
✅ Ejecutar después de agregar documentos
✅ Ejecutar periódicamente (ej. semanalmente)

**Qué verifica:**
- ✓ Existe el índice y está ready
- ✓ Todos los documentos en disk están indexados
- ✓ Recuperación de cubismo y barroco funciona
- ✓ No hay archivos faltantes

### 2. Servicio RAG (app/models/rag/service.py)

Funciones principales:

```python
# Reconstruir índice desde cero (SI ES NECESARIO)
from app.models.rag import service
result = service.rebuild_index()
print(f"Chunks indexados: {result['chunks']}")

# Verificar estado
status = service.index_status()
print(f"Índice listo: {status['ready']}")

# Recuperar documentos
hits = service.retrieve("¿Qué es el cubismo?", k=10)
print(f"Documentos: {len(hits)}")

# Hacer pregunta completa
response = service.ask("¿Qué es el cubismo?", k=10)
print(response['answer'])
```

### 3. Evaluación (app/models/rag/evaluation.py)

```python
# Evaluar recuperación
from app.models.rag import evaluation
result = evaluation.evaluate_retrieval(k=10, sweep=True)
print(f"Cubismo F1: {result['barrido_k'][4]['f1']}")  # k=10

# Evaluar respuestas generadas
result_gold = evaluation.evaluate_gold(judge=True, k=10)
print(result_gold['resumen']['rouge1_f1'])
```

## Recomendaciones de Mantenimiento

### Diario/Por Cada Cambio

```bash
# Después de agregar documentos, ejecutar:
python validate_rag_index.py
```

### Semanal

```bash
# Test rápido de retrieval
python -c "
import sys; sys.path.insert(0, '.')
from app.models.rag import service
results = service.retrieve('¿Qué es el cubismo?', k=10)
assert len(results) >= 5, 'Retrieval deficiente!'
print(f'✓ Retrieval OK: {len(results)} documentos')
"
```

### Mensual

```bash
# Evaluación completa
python -c "
import sys; sys.path.insert(0, '.')
from app.models.rag import evaluation
result = evaluation.evaluate_retrieval(k=10)
print('Cubismo:', result['promedio'])
"
```

### Trimestral

```bash
# Rebuild preventivo (es seguro ejecutarlo)
python -c "
import sys; sys.path.insert(0, '.')
from app.models.rag import service
result = service.rebuild_index()
print(f'Rebuild completado: {result[\"chunks\"]} chunks')
"
```

## Síntomas de Índice Corrupto

⚠️ **ALERTA:** Si ves alguno de estos síntomas, ejecutar rebuild inmediatamente:

1. **Retrieval deficiente de un tema específico**
   - Síntoma: Una tema (ej. cubismo) no recupera documentos
   - Acción: `python validate_rag_index.py` → `rebuild_index()` si es necesario

2. **Agregar documentos empeora los resultados**
   - Síntoma: F1 cae después de agregar datos
   - Acción: Rebuild inmediato

3. **Índice incompleto**
   - Síntoma: `indexed_chunks` < `expected_chunks`
   - Acción: Rebuild inmediato

4. **Cobertura de archivos < 100%**
   - Síntoma: Validador muestra archivos faltantes
   - Acción: Rebuild inmediato

## Recuperación de Falla Total

Si el sistema falla completamente:

```python
from app.models.rag import service
from app import config
import os

# 1. Backup de índice corrupto (OPCIONAL)
# os.rename(config.RAG_DB_DIR, config.RAG_DB_DIR + '.backup')

# 2. Rebuild desde cero (elimina índice viejo automáticamente)
result = service.rebuild_index()

# 3. Validar
result2 = service.index_status()
assert result2['ready'], "Rebuild falló!"

# 4. Test
hits = service.retrieve("¿Qué es el cubismo?", k=10)
assert len(hits) >= 5, "Retrieval aún deficiente"

print("✓ Sistema recuperado")
```

## Archivos Importantes

```
Artizan/
├── app/models/rag/
│   ├── service.py           ← Lógica principal del RAG
│   ├── evaluation.py        ← Métricas de evaluación
│   ├── retrieval_optimizations.py
│   ├── generation_improvements.py
│   └── comprehensive_evaluation.py
├── rag_data/
│   └── archivos_texto_json/ ← Documentos fuente (22 archivos)
├── rag_db/
│   └── chroma.sqlite3       ← Índice ChromaDB (NO editar)
├── validate_rag_index.py    ← Validación
├── evaluacion_post_rebuild.json ← Resultados recientes
├── DIAGNOSTICO_SOLUCION_CUBISMO.md ← Análisis técnico
└── RESUMEN_EJECUTIVO_SOLUCION.md ← Este resumen
```

## Configuración Actual

```python
# app/config.py
RAG_CHUNK_SIZE = 512        # Tamaño de chunks
RAG_CHUNK_OVERLAP = 0       # Sin solapamiento
RAG_TOP_K = 10              # Documentos a recuperar por defecto
RAG_MIN_MENTIONS = 2        # Menciones mínimas para considerar relevante
RAG_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"  # Modelo multilíngue
RAG_LLM_MODEL = "llama2"    # LLM para generación
RAG_DATA_DIR = "rag_data"   # Carpeta de documentos
RAG_DB_DIR = "rag_db"       # Carpeta de índice
```

## Documentación Relacionada

- `RESUMEN_EJECUTIVO_SOLUCION.md` - Resumen de la solución
- `DIAGNOSTICO_SOLUCION_CUBISMO.md` - Análisis técnico detallado
- `COMPARACION_ANTES_DESPUES.json` - Métricas comparativas
- `evaluacion_post_rebuild.json` - Evaluación completa actual
- `RAG_IMPROVEMENT_PLAN.md` - Plan original de mejoras
- `GUIA_MEJORAS_RAG.md` - Guía de mejoras implementadas

## Contacto / Soporte

Si encontras problemas:

1. ✅ Ejecutar `validate_rag_index.py`
2. ✅ Revisar logs en `logs/requests.log`
3. ✅ Consultar documentación mencionada arriba
4. ✅ Si persiste, hacer rebuild

---

**Última actualización:** 2026-11-13  
**Estado:** ✅ Sistema funcional y restaurado  
**Cubismo F1:** 0.667 (antes: 0.222)
