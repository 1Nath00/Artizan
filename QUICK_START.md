# 🚀 QUICK START - Sistema RAG Mejorado

**⏱️ Tiempo de lectura:** 2 minutos  
**⏱️ Tiempo de ejecución:** 10 segundos - 15 minutos  
**✅ Estado:** Listo para ejecutar AHORA

---

## 1️⃣ VALIDAR INMEDIATAMENTE (10 seg)

```bash
cd C:\Users\natal\programas\Artizan
python validar_rag_mejorado.py
```

**Resultado esperado:**
```
[OK] Imports - All modules imported successfully
[OK] Deduplicacion - Reduced 3 chunks to 2 (dedup_rate=0.33)
[OK] Validacion de Citas - Extracted 3 citations: [1], [2], [3]
[OK] Estadisticas - Response has 245 words, 12 sentences, 3 paragraphs
[OK] Compatibilidad - retrieve, build_messages, ask are backward compatible

RESULTADO: 5/5 tests PASADOS ✓
```

Si ves esto → **El sistema está funcionando correctamente** ✅

---

## 2️⃣ ANALIZAR CONFIGURACIÓN (5 seg)

```bash
python analizar_chunking.py
```

**Resultado esperado:**
```
Configuración actual:
- Tamaño de chunks: 900 caracteres
- Solapamiento: 150 caracteres
- Número total: 189 chunks

Recomendaciones:
- Considerar aumentar K de 5 a 10-12
- Verificar fragmentación < 20%
```

---

## 3️⃣ EJECUTAR DIAGNÓSTICO (10-15 min)

### Opción A: Prueba Rápida (2-3 min)
```bash
python test_rag_improvements.py
```

**Salida:** `test_k_results.csv`  
**Para saber:** Cuál K es mejor (5, 10, 15, 20?)

### Opción B: Diagnóstico Completo (10-15 min)
```bash
python diagnostico_rag_mejorado.py
```

**Salidas:**
- `diagnostico_mejorado.jsonl` - Resultados detallados
- `diagnostico_comparacion.csv` - Resumen de métricas

**Para saber:** 
- Precision actual
- Recall actual
- F1 Score actual
- Latencia desglosada
- Calidad de citas

---

## 📊 INTERPRETAR RESULTADOS

### test_k_results.csv

| K | Precision | Recall | F1 | Latencia |
|---|-----------|--------|----|----|
| 1 | 0.80 | 0.206 | 0.300 | 0.45s |
| 10 | 0.62 | 0.605 | 0.556 | 0.67s |
| 20 | 0.50 | 0.80 | 0.61 | 0.89s |

**Cómo elegir K:**
- Si Precision > Recall → K es bueno
- Si Recall muy bajo → aumentar K
- Si F1 es máximo → K es óptimo
- Si Latencia > 1s → K es muy alto

### diagnostico_comparacion.csv

| Métrica | Antes | Después | Mejora |
|---------|-------|---------|--------|
| Precision | 0.62 | ? | ? |
| Recall | 0.605 | ? | ? |
| F1 Score | 0.556 | ? | ? |
| Latencia | 18.16s | ? | ? |

**Cómo leer:**
- ✅ Si "Después" > "Antes" → Mejora exitosa
- ❌ Si "Después" < "Antes" → Necesita ajuste
- ⏳ Si "Después" = ? → Aún no ejecutado

---

## 🔧 AJUSTES RECOMENDADOS

### Si Precision es baja (< 0.65)
```python
# En .env
RAG_TOP_K=10          # Aumentar de 5 a 10
RAG_CHUNK_SIZE=1000   # Chunks más grandes
```

Ejecutar: `POST /models/rag/index` (reindexar)

### Si Recall es bajo (< 0.60)
```python
# En .env
RAG_TOP_K=15          # Aumentar más
RAG_CHUNK_OVERLAP=200 # Más solapamiento
```

Ejecutar: `POST /models/rag/index` (reindexar)

### Si Latencia es alta (> 20s)
```python
# Opción 1: Reducir K
RAG_TOP_K=8

# Opción 2: Chunks más pequeños
RAG_CHUNK_SIZE=600
```

No reindexar, cambios inmediatos.

### Si hay alucinaciones
Ya implementado en el nuevo prompt. Verificar con:
```bash
python diagnostico_rag_mejorado.py
# Ver métrica: "hallucination_judge"
```

---

## 📈 FLUJO COMPLETO (30 min)

```bash
# Paso 1: Validar (10 seg) ✓
python validar_rag_mejorado.py

# Paso 2: Analizar (5 seg) ✓
python analizar_chunking.py

# Paso 3: Diagnosticar (10-15 min) ✓
python diagnostico_rag_mejorado.py

# Paso 4: Comparar resultados
# Abre: diagnostico_comparacion.csv
# Compara con: diagnostico_antes.csv

# Paso 5: Ajustar si necesario
# Edita: .env
# Ejecuta: POST /models/rag/index

# Paso 6: Re-validar
python diagnostico_rag_mejorado.py
```

---

## 💾 ARCHIVOS IMPORTANTES

### Configuración
| Archivo | Ubicación | Acción |
|---------|-----------|--------|
| `.env` | Raíz | Editar valores de K, chunk size |
| `RAG_IMPROVEMENT_PLAN.md` | Raíz | Leer el plan completo |

### Resultados
| Archivo | Generado por | Contiene |
|---------|-------------|----------|
| `test_k_results.csv` | `test_rag_improvements.py` | Metrics para K: 1,3,5,8,10,12,15,20 |
| `diagnostico_mejorado.jsonl` | `diagnostico_rag_mejorado.py` | Resultados detallados (10 preguntas) |
| `diagnostico_comparacion.csv` | `diagnostico_rag_mejorado.py` | Resumen agregado |
| `diagnostico_antes.csv` | Línea base | Para comparación |

### Módulos
| Archivo | Ubicación | Función |
|---------|-----------|---------|
| `retrieval_optimizations.py` | `app/models/rag/` | Deduplicación, MMR |
| `generation_improvements.py` | `app/models/rag/` | Citas, alucinaciones |
| `comprehensive_evaluation.py` | `app/models/rag/` | Evaluación integral |

---

## ❓ PREGUNTAS FRECUENTES

### P: ¿Es seguro ejecutar estos scripts?
**R:** Sí, 100% seguros. Solo leen datos, no modifican nada.

### P: ¿Cuánto toman en ejecutarse?
**R:** 
- Validación: 10 segundos
- Análisis: 5 segundos
- Pruebas K: 2-3 minutos
- Diagnóstico: 10-15 minutos

### P: ¿Puedo ejecutarlos en paralelo?
**R:** No recomendado. Ejecuta secuencialmente.

### P: ¿Debo reindexar después de cambiar K?
**R:** No. K solo cambia cuántos resultados se recuperan. Reindexar si cambias chunk size/overlap.

### P: ¿Qué pasa si los resultados no mejoran?
**R:** 
1. Revisa `analizar_chunking.py`
2. Prueba diferentes K (5, 10, 15, 20)
3. Ajusta chunk size (600-1000)
4. Revisa documentos de origen

### P: ¿Es reversible?
**R:** Sí, completamente. Hay backup en `service_backup.py`.

---

## 📞 AYUDA RÁPIDA

### "No sé por dónde empezar"
```bash
python validar_rag_mejorado.py
```
→ Si dice 5/5 PASADOS, todo está bien. Ve al paso 2.

### "Quiero saber qué K usar"
```bash
python test_rag_improvements.py
```
→ Abre `test_k_results.csv` y busca el K con F1 más alto.

### "Quiero ver las métricas completas"
```bash
python diagnostico_rag_mejorado.py
```
→ Abre `diagnostico_comparacion.csv` y compara con `diagnostico_antes.csv`.

### "Algo no funciona"
```bash
python validar_rag_mejorado.py
```
→ Si muestra error, lee [GUIA_MEJORAS_RAG.md](GUIA_MEJORAS_RAG.md) sección "Troubleshooting".

---

## ✅ CHECKLIST

### Antes de empezar
- [ ] Estoy en: `C:\Users\natal\programas\Artizan`
- [ ] Tengo Python 3.10+
- [ ] Tengo Ollama ejecutándose
- [ ] La BD vectorial está accesible

### Durante la ejecución
- [ ] Validación: 5/5 PASADOS ✓
- [ ] Análisis: Recomendaciones leídas ✓
- [ ] Pruebas: K óptimo identificado ✓
- [ ] Diagnóstico: CSV generado ✓

### Después de los ajustes
- [ ] Cambios aplicados a `.env` ✓
- [ ] `POST /models/rag/index` ejecutado ✓
- [ ] Re-validación completada ✓
- [ ] Mejoras verificadas ✓

---

## 🎯 OBJETIVO FINAL

**Obtener una respuesta clara de:**
```
¿El sistema RAG mejoró después de los cambios?
SÍ/NO, porque:
- Precision: antes 0.62 → después ?
- Recall: antes 0.605 → después ?
- F1 Score: antes 0.556 → después ?
- Latencia: antes 18.16s → después ?
```

**Cómo lograrlo:**
1. Ejecuta `diagnostico_rag_mejorado.py`
2. Abre `diagnostico_comparacion.csv`
3. Compara con `diagnostico_antes.csv`
4. Listo ✅

---

## 📖 DOCUMENTACIÓN DISPONIBLE

| Documento | Audiencia | Tiempo |
|-----------|-----------|--------|
| **Este archivo** | Todos | 2 min |
| `RESUMEN_EJECUTIVO_MEJORAS.md` | Ejecutivos | 5 min |
| `GUIA_MEJORAS_RAG.md` | Usuarios | 10 min |
| `ESPECIFICACION_TECNICA_CAMBIOS.md` | Desarrolladores | 15 min |
| `RAG_IMPROVEMENT_PLAN.md` | Tech Leads | 10 min |
| `STATUS_IMPLEMENTACION.md` | Revisión general | 5 min |
| `INDICE_DOCUMENTACION.md` | Navegación | 2 min |

---

## 🚀 COMIENZA AHORA

```bash
# Paso 1 (10 seg)
cd C:\Users\natal\programas\Artizan
python validar_rag_mejorado.py

# ¿Ves 5/5 PASADOS? → Ve al Paso 2
# ¿Ves ERROR? → Lee troubleshooting en GUIA_MEJORAS_RAG.md

# Paso 2 (5 seg)
python analizar_chunking.py

# Paso 3 (10-15 min)
python diagnostico_rag_mejorado.py

# ¡Listo! ✅
```

**Tiempo total: 30 minutos**  
**Resultado: Métricas antes/después de mejoras**  
**Próximo: Decidir ajustes basado en resultados**

---

**¿Preguntas?** → Lee [GUIA_MEJORAS_RAG.md](GUIA_MEJORAS_RAG.md)  
**¿Detalles técnicos?** → Lee [ESPECIFICACION_TECNICA_CAMBIOS.md](ESPECIFICACION_TECNICA_CAMBIOS.md)  
**¿Arquitectura?** → Lee [RAG_IMPROVEMENT_PLAN.md](RAG_IMPROVEMENT_PLAN.md)

---

**Versión:** 1.0.0  
**Estado:** ✅ LISTO PARA EJECUTAR  
**Ultima actualización:** 2025
