# Guía de Activación: Ground Truth por Pregunta

## Estado Actual

Se han aplicado los cambios quirúrgicos al sistema de evaluación de retrieval en `app/models/rag/evaluation.py`:

✓ `RELEVANT_BY_QUESTION` definido con 10 preguntas  
✓ Función `verify_filenames()` implementada  
✓ Función `eval_retrieval(k, relevant=None)` modificada  
✓ Función `evaluate_retrieval()` actualizada  
✓ Deduplicación por filename activada  

## Problema Detectado

`verify_filenames()` está detectando desajustes entre los filenames en `RELEVANT_BY_QUESTION` y los archivos reales en el corpus:

```
ERROR: Filenames faltantes:
  - cubismo-2.txt (usado en 3 preguntas)
  - El_Período_Barroco.txt (usado en 3 preguntas)
  - QUE_ES_EL_BARROCO_1.txt (usado en 5 preguntas)
  ... (11 totales)
```

## Solución: Dos Opciones

### OPCION A: Actualizar RELEVANT_BY_QUESTION con filenames reales

1. **Listar archivos reales en el corpus:**
   ```bash
   python -c "
   from app import config
   from app.models.rag import service
   docs = service.load_documents(config.RAG_DATA_DIR)
   for d in sorted(set(doc['filename'] for doc in docs)):
       print(d)
   "
   ```

2. **Actualizar RELEVANT_BY_QUESTION** en `app/models/rag/evaluation.py`:
   - Reemplazar nombres de archivos con los reales del corpus
   - Ejecutar `python test_eval_changes.py` para validar
   - Ejecutar `python test_integration_eval.py` para confirmar

### OPCION B: Usar script de mapeo automático (si los contenidos son correctos)

Si los documentos existen pero con nombres diferentes:

```python
from app import config
from app.models.rag import service
import re

docs = service.load_documents(config.RAG_DATA_DIR)
corpus = {d['filename']: d for d in docs}

# Mapeo manual de "intent" a filename real
# Ej: "cubismo" en el nombre -> buscar archivo con ese contenido
def find_matching_file(pattern: str, corpus: dict) -> str:
    """Busca un archivo que contenga el patrón en su nombre o contenido."""
    for fname, doc in corpus.items():
        if pattern.lower() in fname.lower():
            return fname
        if pattern.lower() in doc['text'].lower():
            return fname
    return None
```

## Próximos Pasos

### 1. Inspeccionar corpus actual

```bash
python -c "
from app import config
from app.models.rag import service
docs = service.load_documents(config.RAG_DATA_DIR)
print(f'Total documentos: {len(set(d[\"filename\"] for d in docs))}')
for fname in sorted(set(d['filename'] for d in docs)):
    print(f'  - {fname}')
"
```

### 2. Actualizar RELEVANT_BY_QUESTION

Editar `app/models/rag/evaluation.py` líneas ~60-130 con nombres reales:

```python
RELEVANT_BY_QUESTION: dict[str, set[str]] = {
    "¿Qué es el cubismo?": {
        "Cubismo.txt",  # NOMBRE REAL
        "El cubismo.txt",  # NOMBRE REAL
        # ...otros nombres reales...
    },
    # ... resto de preguntas con nombres reales ...
}
```

### 3. Validar cambios

```bash
# Test unitarios
python test_eval_changes.py

# Test de integración
python test_integration_eval.py

# Test de evaluación real (si corpus está listo)
python -c "
from app.models.rag.evaluation import evaluate_retrieval
try:
    resultado = evaluate_retrieval(k=5, sweep=False)
    print('Precision media:', resultado['promedio']['precision'])
    print('Recall media:', resultado['promedio']['recall'])
    print('F1 media:', resultado['promedio']['f1'])
except Exception as e:
    print(f'Error: {e}')
"
```

## Reglas de Oro

1. **NUNCA adivines nombres de archivos**
   - `verify_filenames()` te lo dirá
   - Si falta un nombre, usa el que existe realmente en el corpus

2. **Los nombres en RELEVANT_BY_QUESTION deben coincidir EXACTAMENTE** con:
   - El campo `filename` en los documentos del corpus
   - Mayúsculas/minúsculas, caracteres especiales, extensiones

3. **Ejecuta verify_filenames() ANTES de reportar OK**
   - Desde `evaluate_retrieval()` automáticamente
   - O manualmente: `from app.models.rag.evaluation import verify_filenames; print(verify_filenames())`

4. **La evaluación es más rigurosa ahora**
   - Recall puede ser más bajo (es lo correcto)
   - Cada pregunta se compara contra su verdadero ground truth
   - Mojibake en filenames será detectado inmediatamente

## Archivo de Referencia

- Cambios aplicados: [evaluation.py](app/models/rag/evaluation.py) líneas 60-386
- Resumen técnico: [RESUMEN_CAMBIOS_EVALUATION.md](RESUMEN_CAMBIOS_EVALUATION.md)
- Tests: [test_eval_changes.py](test_eval_changes.py), [test_integration_eval.py](test_integration_eval.py)

## Preguntas Frecuentes

**P: ¿Por qué está fallando `verify_filenames()`?**
R: Porque hay desajustes entre nombres en GT y corpus. Esto es CORRECTO. Actualiza RELEVANT_BY_QUESTION con nombres reales.

**P: ¿Puedo ignorar los errores de `verify_filenames()`?**
R: NO. La función está diseñada para detectar problemas críticos. Si ignoras, las métricas serán incorrectas.

**P: ¿Cómo obtengo los nombres reales?**
R: `from app.models.rag import service; docs = service.load_documents(...); print(set(d['filename'] for d in docs))`

**P: ¿Cambiamos la lógica de evaluación?**
R: NO. Cambiamos a QUÉ se evalúa (ground truth por pregunta vs por tema). Las métricas (precision/recall/F1) son idénticas.
