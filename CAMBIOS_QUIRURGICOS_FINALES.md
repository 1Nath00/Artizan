# CAMBIOS QUIRURGICOS APLICADOS: Ground Truth por Pregunta

## Resumen Ejecutivo

Se completó la implementación de evaluación de retrieval por PREGUNTA en lugar de por TEMA. Los cambios son **quirúrgicos, precisos y no refactorizan nada existente**.

### Estado Final: ✓ COMPLETADO

- ✓ RELEVANT_BY_QUESTION definido con filenames correctos
- ✓ verify_filenames() implementada y validando
- ✓ eval_retrieval() modificada para aceptar relevant=None
- ✓ evaluate_retrieval() actualizada para usar RELEVANT_BY_QUESTION
- ✓ Deduplicación por filename activa
- ✓ Validación de encoding (mojibake) automática
- ✓ Todos los tests pasando (7/7 + integración)
- ✓ Sintaxis validada

---

## Cambios Detallados

### 1. RELEVANT_BY_QUESTION (líneas 60-130)

**Antes:**
```python
# No existía; se usaba relevant_docs() que devolvía dict[tema] -> set[docs]
RELEVANT_BY_QUESTION no existía
```

**Ahora:**
```python
RELEVANT_BY_QUESTION: dict[str, set[str]] = {
    # 10 preguntas (5 cubismo, 5 barroco)
    # Cada pregunta mapea a su conjunto relevante de filenames
    "¿Qué es el cubismo?": {
        "El cubismo.txt",
        "cubismo-2.txt",
        "Manifiesto-del-Cubismo-1913.txt",
        "manual-basico-de-historia-del-arte-m-pilar-de-la-pena-gomez-1529.txt",
    },
    # ... resto de preguntas
}
```

**Impacto:**
- Cada pregunta tiene su propio ground truth específico
- Filenames coinciden exactamente con los del corpus (incluyendo mojibake)
- Validado con verify_filenames()

---

### 2. verify_filenames() (líneas 318-335)

**Nueva función:**
```python
def verify_filenames() -> dict[str, list[str]]:
    """Valida que los filenames en RELEVANT_BY_QUESTION existen en el corpus.
    Compara por nombre base (basename) para evitar problemas con rutas relativas.
    Devuelve dict[filename -> lista de preguntas donde no se encuentra].
    """
```

**Propósito:**
- Detectar mojibake o desajustes entre GT y corpus ANTES de evaluar
- Comparar por basename (nombre del archivo sin ruta)
- Retorna dict vacío si OK, dict con faltantes si hay problemas

**Invocación:**
- Automática en evaluate_retrieval() al inicio
- Lanza ValueError si hay filenames faltantes

---

### 3. eval_retrieval(k, relevant=None) (líneas 337-360)

**Cambio de firma:**
```python
# ANTES
def eval_retrieval(k: int, relevant: dict[str, set[str]]) -> list[dict[str, Any]]:

# AHORA
def eval_retrieval(k: int, relevant: dict[str, set[str]] | None = None) -> list[dict[str, Any]]:
    """Evalúa retrieval por PREGUNTA usando su propio set de relevantes (RELEVANT_BY_QUESTION).
    Si relevant no se proporciona, usa RELEVANT_BY_QUESTION directamente.
    """
    if relevant is None:
        relevant = RELEVANT_BY_QUESTION
```

**Cambios de lógica:**
- Por defecto usa RELEVANT_BY_QUESTION directamente
- Mantiene deduplicación: `got = list(dict.fromkeys(h["filename"] for h in service.retrieve(q, k)))`
- Busca GT por pregunta exacta: `gt = relevant.get(q, set())`
- Calcula precision/recall/f1 por pregunta

---

### 4. evaluate_retrieval(k=None, sweep=True) (líneas 362-386)

**Cambios:**
```python
def evaluate_retrieval(k: int | None = None, sweep: bool = True) -> dict[str, Any]:
    k = k or config.RAG_TOP_K
    
    # NUEVO: Verificar que los filenames en el GT existen en el corpus
    missing = verify_filenames()
    if missing:
        raise ValueError(f"Filenames no encontrados en el corpus: {missing}")
    
    # CAMBIO: Pasar RELEVANT_BY_QUESTION directamente
    rows = eval_retrieval(k, RELEVANT_BY_QUESTION)
    
    result: dict[str, Any] = {
        "k": k,
        # CAMBIO: relevantes ahora es por PREGUNTA, no por TEMA
        "relevantes": {q: sorted(s) for q, s in RELEVANT_BY_QUESTION.items()},
        "preguntas": rows,
        "promedio": {m: _mean([r[m] for r in rows]) for m in ("precision", "recall", "f1")},
    }
    
    if sweep:
        out = []
        for kk in (1, 3, 5, 8, 10):
            # CAMBIO: Usar RELEVANT_BY_QUESTION en sweep
            d = eval_retrieval(kk, RELEVANT_BY_QUESTION)
            out.append({"k": kk, **{m: _mean([r[m] for r in d]) for m in ("precision", "recall", "f1")}})
        result["barrido_k"] = out
```

---

## Matriz de Cambios

| Componente | Antes | Ahora | Estado |
|-----------|-------|-------|--------|
| RELEVANT_BY_QUESTION | No existía | dict[pregunta] -> set[docs] | ✓ |
| verify_filenames() | No existía | Valida GT vs corpus | ✓ |
| eval_retrieval firma | relevant requerido | relevant=None | ✓ |
| eval_retrieval default | N/A | Usa RELEVANT_BY_QUESTION | ✓ |
| evaluate_retrieval | Llama relevant_docs() | Llama verify_filenames(), usa RELEVANT_BY_QUESTION | ✓ |
| "relevantes" salida | dict[tema] | dict[pregunta] | ✓ |
| Deduplicación | Implícita | Explícita dict.fromkeys | ✓ |
| Encoding validation | No | Automática en verify_filenames() | ✓ |

---

## Testing

### Test 1: test_eval_changes.py (7/7 PASS)
```
[OK] RELEVANT_BY_QUESTION existe y esta poblado
[OK] Estructura de RELEVANT_BY_QUESTION
[OK] Consistencia entre QUESTIONS y RELEVANT_BY_QUESTION
[OK] Estructura de filenames en GT
[OK] Deduplicacion por filename en eval_retrieval
[OK] Funcion verify_filenames es callable
[OK] eval_retrieval acepta parametro relevant opcional
```

### Test 2: test_integration_eval.py (PASS)
```
[OK] Todos los filenames en RELEVANT_BY_QUESTION existen en el corpus
Total: 10 preguntas, 36 GT doc-question pairs
[OK] INTEGRACION COMPLETADA EXITOSAMENTE
```

### Validación de sintaxis
```bash
python -m py_compile app/models/rag/evaluation.py
# Exit code 0 (OK)
```

---

## Comportamiento Esperado

### Antes
```python
relevant = relevant_docs()  # dict[tema] -> set[docs]
# "cubismo": {doc1, doc2, doc3, doc4, doc5, doc6, doc7}
# "barroco": {doc1, doc2, doc3, doc4, doc5, doc6, doc7, doc8, doc9}

eval_retrieval(10, relevant)  # Cada pregunta se comparaba contra TODOS los docs del tema
# Problema: "¿Qué es el cubismo?" se evaluaba contra los mismos 7 docs que
#           "Define el cubismo como movimiento artístico." aunque podrían
#           haber documentos más relevantes para una que para otra.
```

### Ahora
```python
# No necesita llamar relevant_docs(); RELEVANT_BY_QUESTION está siempre disponible

eval_retrieval(10)  # Usa RELEVANT_BY_QUESTION directamente
# "¿Qué es el cubismo?": {doc1, doc2, doc3, doc4}
# "Define el cubismo como movimiento artístico.": {doc1, doc2, doc3, doc4}
# "¿Cuáles son las características del cubismo?": {doc1, doc2, doc3, doc5}
# ... cada pregunta tiene su propio ground truth

# Resultado: precision/recall/f1 correcto por pregunta
```

---

## Garantías

✓ **Quirúrgico**: Solo cambios dirigidos, sin refactorización  
✓ **Completo**: Todos los cambios listados implementados  
✓ **Validado**: Sintaxis correcta, 7/7 tests pasan  
✓ **Backward compatible**: eval_retrieval() es callable con o sin relevant  
✓ **Robusto**: verify_filenames() detecta encoding issues  
✓ **Documentado**: Este archivo explica cada cambio  

---

## Próximos Pasos (Opcionales)

### Si quieres optimizar Jaccard robustness (sugerencia #3)
Ver archivo GUIA_MEJORAS_RAG.md o contactar con el ingeniero senior.

### Para usar en evaluación real
```python
from app.models.rag.evaluation import evaluate_retrieval

# Ejecutar evaluación completa (con sweep de k)
resultado = evaluate_retrieval(k=10, sweep=True)

# Ver métricas promedio
print(resultado['promedio'])
# {'precision': 0.75, 'recall': 0.85, 'f1': 0.80}

# Ver robustez por tema
print(resultado['robustez_jaccard'])
# {'cubismo': 0.65, 'barroco': 0.72}
```

---

## Archivos Generados

- [RESUMEN_CAMBIOS_EVALUATION.md](RESUMEN_CAMBIOS_EVALUATION.md) - Resumen técnico
- [GUIA_ACTIVACION_GT_PREGUNTAS.md](GUIA_ACTIVACION_GT_PREGUNTAS.md) - Guía de activación
- [test_eval_changes.py](test_eval_changes.py) - Tests unitarios (7 casos)
- [test_integration_eval.py](test_integration_eval.py) - Test de integración
- [corpus_filenames.json](corpus_filenames.json) - Mapeo de corpus
- [fix_relevant_by_question.py](fix_relevant_by_question.py) - Script de corrección (helper)
- [corpus_names_cleaned.py](corpus_names_cleaned.py) - Archivo de referencia de nombres

---

## Notas Importantes

1. **Mojibake en corpus**: Algunos filenames en el corpus contienen caracteres con encoding issues (ej: `El_Per├¡odo_Barroco.txt`). Esto es normal y está manejado por verify_filenames().

2. **Rutas relativas**: Los filenames en el corpus incluyen rutas relativas (ej: `archivos_texto_json\filename.txt`). verify_filenames() compara por basename para evitar este problema.

3. **Impacto en métricas**: Los F1 scores pueden cambiar significativamente respecto a antes (especialmente hacia arriba si el GT era incorrecto antes). Esto es CORRECTO.

4. **Serialización**: Los sets en RELEVANT_BY_QUESTION se convierten a listas en la salida JSON (ver línea 376: `sorted(s)`).

---

## Contacto

Ingeniero Senior Python / RAG Evaluation System
Versión: 1.0 (Corrección Quirúrgica)
Fecha: 2026-11-15
