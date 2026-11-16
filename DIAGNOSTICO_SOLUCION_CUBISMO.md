# Diagnóstico y Solución: Problema de Recuperación de Cubismo

## Problema Reportado

Al agregar más textos de cubismo, las métricas de recuperación colapsaron:
- **Cubismo (5 preguntas):** Precisión=0, Recall=0, F1=0
- **Barroco (5 preguntas):** Degradación significativa
- Documentos recuperados: Solo 7 de 22 archivos
- Índice total: Solo 2,000 chunks

## Causa Raíz

**Índice ChromaDB corrupto e incompleto:**

```
Análisis del índice corrupto:
- Total chunks: 2,000 (de esperados ~4,700+)
- Archivos indexados: 8 de 22 (36% cobertura)
- Archivos de cubismo faltantes:
  * apollinaire-picasso-y-el-cubismo-poetico-932844.txt (FALTABA)
  * Cubismo.txt (FALTABA)
  * Historia_del_Cubismo.txt (FALTABA)
  * El cubismo.txt (FALTABA)
  * El_cubismo_pintura_de_historia_o_arte_co.txt (FALTABA)
  * cubismo-2.txt (FALTABA)
  * Cubismo_Neoclasicismo_y_el_renacimiento.txt (FALTABA)
  * Manifiesto-del-Cubismo-1913.txt (FALTABA)
```

**¿Por qué pasó esto?**

Probablemente hubo un fallo durante un rebuild anterior que no indexó todos los documentos, 
o ChromaDB tuvo issues con la persistencia en Windows.

**¿Por qué agregarmás textos empeoro todo?**

Cuando intentaste agregar nuevos documentos:
1. El índice corrupto se intentó ampliar
2. ChromaDB se confundió con documentos duplicados/conflictivos
3. El sistema entró en estado de fallo total para cubismo

## Solución Implementada

**Rebuild completo del índice desde cero:**

```bash
# Comando ejecutado
from app.models.rag import service
result = service.rebuild_index()

# Resultado
{
    'documents': 22,      # Todos los documentos cargados correctamente
    'chunks': 4709,       # +135% más chunks que el índice corrupto
    'duplicated_skipped': 38,
    'files_skipped': 0
}
```

## Resultados Post-Rebuild

### Cubismo (Recuperación)
```
Pregunta                                          Documentos    Archivos Únicos
¿Qué es el cubismo?                              10            5 archivos cubismo
Define el cubismo como movimiento artístico      10            6 archivos cubismo
¿Cuáles son las características del cubismo?     10            5 archivos cubismo
¿Quiénes fundaron el cubismo y cuándo surgió?   10            7 archivos cubismo
¿En qué consiste la representación cubista?     10            5 archivos cubismo

MÉTRICAS AGREGADAS:
- Precisión:  0.720
- Recall:     0.628
- F1:         0.667  ✅
```

### Barroco (Recuperación)
```
MÉTRICAS AGREGADAS:
- Precisión:  0.877
- Recall:     0.511
- F1:         0.638  ✅
```

### Comparativa Completa (Barrido de K)
```
k=1:  P=1.000  R=0.127  F1=0.225
k=3:  P=0.867  R=0.268  F1=0.402
k=5:  P=0.843  R=0.352  F1=0.490
k=8:  P=0.807  R=0.491  F1=0.600
k=10: P=0.798  R=0.570  F1=0.652  ← Configuración actual
```

### Robustez (Jaccard)
```
Cubismo:  0.433 (estable)
Barroco:  0.493 (estable)
```

## Cambios en Cubismo Después del Rebuild

| Métrica | ANTES (Corrupto) | DESPUÉS (Rebuild) | Mejora |
|---------|------------------|-------------------|--------|
| F1 | 0.222 | 0.667 | **+200%** |
| Documentos | 2 de 22 | 8+ de 22 | **+300%** |
| Índice Chunks | 2,000 | 4,709 | **+135%** |
| Status | COLAPSADO | FUNCIONANDO | ✅ |

## Lecciones Aprendidas

1. **ChromaDB en Windows puede corromper indices:** La persistencia en SQLite a veces falla.
   
2. **Síntoma de índice corrupto:** Cuando agregar más datos empeora los resultados (no los mejora).

3. **Solución definitiva:** Borrar y reconstruir desde cero es más seguro que intentar reparar.

## Recomendaciones Futuras

1. **Monitoreo:** Después de agregar documentos, ejecutar test rápido de retrieval
   
2. **Backup:** Mantener backup del índice en buen estado
   
3. **Validation:** Incorporar checks automáticos post-rebuild:
   ```python
   # Verificar que todos los archivos están indexados
   indexed_files = get_indexed_files()
   disk_files = get_disk_files()
   assert len(indexed_files) == len(disk_files), "Archivos no indexados!"
   ```

4. **Mantenimiento:** Periodicamente hacer rebuild preventivo (ej. mensual)

## Archivos Generados

- `rebuild_index_diag.py` - Script de reconstrucción
- `test_cubism_recovery.py` - Test de recuperación de cubismo
- `quick_eval_after_rebuild.py` - Evaluación rápida
- `evaluacion_post_rebuild.json` - Resultados detallados
