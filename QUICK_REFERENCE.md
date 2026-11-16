# Quick Reference - Cubismo Problem Resolution

## 🚨 El Problema
```
Cubismo: F1 = 0 (FALLO TOTAL)
Barroco: F1 = 0.465 (DEGRADADO)
Documentos: 7 de 22 recuperados
```

## ✅ La Solución
```python
from app.models.rag import service
service.rebuild_index()
```

## 📊 Los Resultados
```
ANTES  →  DESPUES
Cubismo F1:     0.222  →  0.667   (+200%)
Índice chunks:  2,000  →  4,709   (+135%)
Cobertura:      36%    →  100%    (+178%)
```

## 🔧 Scripts Disponibles

### 1. Validar Índice
```bash
python validate_rag_index.py
```
✅ Ejecutar después de cambios
✅ Busca problemas temprano

### 2. Usar el Sistema
```python
from app.models.rag import service

# Pregunta
answer = service.ask("¿Qué es el cubismo?")
print(answer['answer'])

# Retrieval
hits = service.retrieve("¿Qué es el cubismo?", k=10)
```

## 📚 Documentación

| Archivo | Propósito | Mejor Para |
|---------|-----------|-----------|
| RESUMEN_VISUAL_RESOLUCION.txt | Visión general | Lectura rápida |
| RESUMEN_EJECUTIVO_SOLUCION.md | Resumen formal | Reportes |
| DIAGNOSTICO_SOLUCION_CUBISMO.md | Análisis técnico | Entender causa raíz |
| GUIA_MANTENIMIENTO_RAG.md | Cómo mantener | Operaciones |
| INDICE_DOCUMENTACION_RESOLUCION.md | Índice completo | Referencia |
| COMPARACION_ANTES_DESPUES.json | Métricas JSON | Análisis automatizado |

## ⚠️ Síntomas de Problema

| Síntoma | Acción |
|---------|--------|
| F1 de tema cae después de agregar docs | `service.rebuild_index()` |
| Archivos no en búsquedas | `validate_rag_index.py` |
| Chunks < 4,000 | Rebuild necesario |
| Cobertura < 100% | Archivo faltante |

## 🎯 Mantenimiento

**Semanal:**
```bash
python validate_rag_index.py
```

**Mensual:**
```python
service.rebuild_index()  # Preventivo
```

**Después de agregar documentos:**
```bash
python validate_rag_index.py
```

## 📈 Métricas Clave

```
Cubismo: P=0.720 R=0.628 F1=0.667 ✅
Barroco: P=0.877 R=0.511 F1=0.638 ✅
k=10:    P=0.798 R=0.570 F1=0.652 ← ÓPTIMO
```

## 📞 Si Hay Problema

1. Ejecuta: `python validate_rag_index.py`
2. Si falla: `service.rebuild_index()`
3. Si persiste: Revisar logs en `logs/requests.log`

## 🎓 Lecciones Aprendidas

1. **Síntoma:** Agregar datos empeora resultados
   - **Causa:** Índice corrupto
   - **Solución:** Rebuild

2. **ChromaDB en Windows**
   - Puede corromper índice con SQLite
   - Rebuild es más seguro que reparar

3. **Monitoreo**
   - Ejecutar health check periódicamente
   - No confiar solo en crecimiento de índice

---

**Status:** ✅ OPERATIVO  
**Última actualización:** 2026-11-13  
**Próxima revisión:** 2026-11-20
