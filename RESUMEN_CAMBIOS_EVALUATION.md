# Resumen de Cambios Quirúrgicos en evaluation.py

## Contexto
Se aplicó una corrección quirúrgica al sistema de evaluación de retrieval del RAG para evaluar cada pregunta contra su propio conjunto de documentos relevantes (RELEVANT_BY_QUESTION), en lugar de usar documentos por tema. Esto mejora la precisión del ground truth y permite medir correctamente recall y precision por pregunta.

## Cambios Aplicados

### 1. **RELEVANT_BY_QUESTION** (ya presente)
- **Ubicación**: Inmediatamente después de `QUESTIONS`
- **Estructura**: `dict[str, set[str]]` con clave = texto EXACTO de pregunta, valor = set de filenames que responden esa pregunta
- **Cobertura**: 10 preguntas (5 cubismo, 5 barroco)
- **Nota**: Contiene commentario sobre "El_Período_Barroco.txt" indicando que debe validarse contra filename real en corpus

### 2. **Nueva función: `verify_filenames()`**
```python
def verify_filenames() -> dict[str, list[str]]:
    """Valida que los filenames en RELEVANT_BY_QUESTION existen en el corpus.
    Devuelve dict[filename -> lista de preguntas donde no se encuentra].
    """
```
- **Propósito**: Detectar mojibake o desajustes entre GT y corpus antes de evaluar
- **Implementación**: Carga corpus, compara contra RELEVANT_BY_QUESTION
- **Retorno**: Dict vacío si OK, dict con filenames faltantes si hay problemas
- **Ubicación**: Antes de `eval_retrieval()`, línea ~318

### 3. **Modificación: `eval_retrieval(k, relevant=None)`**
**Cambio de firma:**
```python
# ANTES
def eval_retrieval(k: int, relevant: dict[str, set[str]]) -> list[dict[str, Any]]:

# AHORA
def eval_retrieval(k: int, relevant: dict[str, set[str]] | None = None) -> list[dict[str, Any]]:
```

**Cambio de lógica:**
- Si `relevant` no se proporciona, usa `RELEVANT_BY_QUESTION` directamente
- Mantiene deduplicación por filename: `got = list(dict.fromkeys(h["filename"] for h in service.retrieve(q, k)))`
- Busca GT por pregunta: `gt = relevant.get(q, set())`
- Mantiene todas las métricas: precision, recall, f1 por pregunta

### 4. **Modificación: `evaluate_retrieval(k=None, sweep=True)`**
**Cambios:**
1. Llama a `verify_filenames()` al inicio y lanza excepción si hay filenames faltantes
2. Reemplaza `relevant = relevant_docs()` por paso directo de `RELEVANT_BY_QUESTION`
3. Cambia estructura de "relevantes" en resultado:
   ```python
   # ANTES
   "relevantes": {t: sorted(s) for t, s in relevant.items()},  # por tema
   
   # AHORA
   "relevantes": {q: sorted(s) for q, s in RELEVANT_BY_QUESTION.items()},  # por pregunta
   ```
4. Pasa `RELEVANT_BY_QUESTION` a `eval_retrieval()` en loop de sweep

## Garantías

✓ Deduplicación por filename preservando orden (mide a nivel de documento, no chunk)
✓ Ground truth por pregunta, no por tema
✓ Validación de filenames antes de evaluar (evita mojibake silencioso)
✓ Cambios quirúrgicos: sin modificación de ROUGE/BLEU/LLM-judge
✓ Backward compatible: `eval_retrieval()` es callable con o sin parámetro `relevant`
✓ Sintaxis validada con `py_compile`
✓ 7/7 tests de validación pasados

## Notas Importantes

1. **Comentario "⚠️" en RELEVANT_BY_QUESTION**: 
   - Se refiere a `El_Período_Barroco.txt` que puede tener problemas de encoding
   - Será detectado automáticamente por `verify_filenames()` si el corpus tiene otro nombre

2. **verify_filenames debe ejecutarse ANTES de evaluar**:
   - Se ejecuta automáticamente en `evaluate_retrieval()` al inicio
   - Si devuelve archivos faltantes, lanza ValueError con detalles

3. **Impacto en métricas**:
   - F1 puede cambiar significativamente respecto a antes (era incorrecto antes)
   - Recall puede ser más bajo si algunas preguntas tienen menos documentos relevantes que otras
   - Esto es CORRECTO: cada pregunta se evalúa contra su verdadero ground truth

## Testing

```bash
python test_eval_changes.py
# [OK] TODOS LOS TESTS PASARON
```

Valida:
- Estructura de RELEVANT_BY_QUESTION
- Consistencia entre QUESTIONS y GT
- Deduplicación por filename
- Firma de funciones
- Importabilidad de verify_filenames
