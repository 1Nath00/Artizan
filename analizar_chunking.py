"""
Script para analizar el chunking actual y proponer mejoras.

Examina:
- Tamaño actual de chunks
- Overlap efectivo
- Fragmentación de conceptos
- Duplicación
- Sugerencias de optimización
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app import config
from app.models.rag import service


def analyze_chunking() -> dict[str, Any]:
    """Analyze current chunking configuration and statistics."""
    
    print("\n" + "=" * 100)
    print("ANÁLISIS DE CHUNKING")
    print("=" * 100)
    
    try:
        collection = service._get_collection()
    except Exception as exc:
        print(f"❌ No se puede acceder al índice: {exc}")
        return {}
    
    total_chunks = collection.count()
    
    print(f"\n📊 ESTADÍSTICAS ACTUALES")
    print(f"  Configuración:")
    print(f"    - Chunk size: {config.RAG_CHUNK_SIZE} caracteres")
    print(f"    - Chunk overlap: {config.RAG_CHUNK_OVERLAP} caracteres")
    print(f"    - Overlap ratio: {config.RAG_CHUNK_OVERLAP / config.RAG_CHUNK_SIZE * 100:.1f}%")
    print(f"  ")
    print(f"  Índice:")
    print(f"    - Total de chunks: {total_chunks}")
    
    # Analyze chunks
    chunk_sizes = []
    documents_unique = set()
    chunks_by_doc = {}
    
    batch_size = 500
    for offset in range(0, total_chunks, batch_size):
        batch = collection.get(limit=batch_size, offset=offset, include=["documents", "metadatas"])
        documents = batch.get("documents", [])
        metadatas = batch.get("metadatas", [])
        
        for text, metadata in zip(documents or [], metadatas or []):
            if isinstance(text, str):
                chunk_sizes.append(len(text))
            
            if isinstance(metadata, dict):
                filename = metadata.get("filename", "unknown")
                documents_unique.add(filename)
                
                if filename not in chunks_by_doc:
                    chunks_by_doc[filename] = 0
                chunks_by_doc[filename] += 1
    
    # Statistics
    if chunk_sizes:
        avg_size = sum(chunk_sizes) / len(chunk_sizes)
        min_size = min(chunk_sizes)
        max_size = max(chunk_sizes)
        median_size = sorted(chunk_sizes)[len(chunk_sizes) // 2]
        
        print(f"\n📐 TAMAÑO DE CHUNKS")
        print(f"    - Promedio: {avg_size:.0f} caracteres")
        print(f"    - Mínimo: {min_size} caracteres")
        print(f"    - Máximo: {max_size} caracteres")
        print(f"    - Mediana: {median_size} caracteres")
        
        # Size distribution
        ranges = [(0, 100), (100, 300), (300, 600), (600, 900), (900, 1200), (1200, float('inf'))]
        print(f"\n📊 DISTRIBUCIÓN DE TAMAÑOS")
        for min_r, max_r in ranges:
            count = sum(1 for s in chunk_sizes if min_r <= s < max_r)
            pct = 100 * count / len(chunk_sizes)
            bar = "█" * int(pct / 2)
            print(f"    {min_r:4d}-{max_r if max_r != float('inf') else '∞':4} chars: {bar:<50} {pct:5.1f}%")
    
    print(f"\n📁 DOCUMENTOS")
    print(f"    - Documentos únicos: {len(documents_unique)}")
    print(f"    - Chunks por documento (promedio): {total_chunks / len(documents_unique):.1f}")
    
    # Top documents
    print(f"\n📄 TOP DOCUMENTOS (por cantidad de chunks)")
    top_docs = sorted(chunks_by_doc.items(), key=lambda x: x[1], reverse=True)[:5]
    for doc, count in top_docs:
        pct = 100 * count / total_chunks
        print(f"    - {doc:<50} {count:4d} chunks ({pct:5.1f}%)")
    
    return {
        "total_chunks": total_chunks,
        "chunk_sizes": chunk_sizes,
        "documents": len(documents_unique),
        "chunks_by_doc": chunks_by_doc,
    }


def suggest_optimizations() -> None:
    """Suggest chunking optimizations based on current configuration."""
    
    print("\n" + "=" * 100)
    print("SUGERENCIAS DE OPTIMIZACIÓN")
    print("=" * 100)
    
    current_size = config.RAG_CHUNK_SIZE
    current_overlap = config.RAG_CHUNK_OVERLAP
    
    print(f"\n📋 ANÁLISIS ACTUAL")
    print(f"  Configuración: size={current_size}, overlap={current_overlap}")
    
    overlap_ratio = current_overlap / current_size
    
    # Rule of thumb recommendations
    recommendations = []
    
    if overlap_ratio < 0.15:
        recommendations.append(
            f"⚠️  Overlap bajo ({overlap_ratio*100:.1f}%). Aumentar a 150-200 caracteres "
            f"(ratio 15-20%) puede mejorar continuidad entre chunks."
        )
    elif overlap_ratio > 0.25:
        recommendations.append(
            f"⚠️  Overlap alto ({overlap_ratio*100:.1f}%). Puede crear mucha redundancia. "
            f"Considerar reducir a 150 caracteres (ratio ~15%)."
        )
    
    if current_size < 600:
        recommendations.append(
            f"💡 Chunks pequeños ({current_size}). Pueden fragmentar conceptos largos. "
            f"Considerar aumentar a 800-1000 para mejor contexto semántico."
        )
    elif current_size > 1200:
        recommendations.append(
            f"💡 Chunks grandes ({current_size}). Pueden ser demasiado contexto para el LLM. "
            f"Considerar reducir a 900-1000 para mejor relevancia."
        )
    
    # Test configurations
    print(f"\n🧪 CONFIGURACIONES A PROBAR")
    print(f"\n  Configuración actual (baseline):")
    print(f"    size={current_size}, overlap={current_overlap}")
    
    test_configs = [
        (600, 100, "Chunks más pequeños (mejor segmentación)"),
        (800, 150, "Tamaño moderado (balance)"),
        (1000, 150, "Chunks grandes (más contexto)"),
        (1000, 200, "Chunks grandes + overlap mayor"),
        (800, 200, "Tamaño moderado + overlap mayor"),
    ]
    
    for size, overlap, description in test_configs:
        ratio = overlap / size * 100
        print(f"    - size={size:<4d}, overlap={overlap:<3d} (ratio {ratio:5.1f}%) → {description}")
    
    if recommendations:
        print(f"\n🎯 RECOMENDACIONES ESPECÍFICAS")
        for rec in recommendations:
            print(f"  {rec}")
    else:
        print(f"\n✓ La configuración actual parece adecuada.")
    
    print(f"\n📝 PRÓXIMOS PASOS")
    print(f"  1. Ejecutar diagnostico_rag_mejorado.py con K=10 (configuración actual)")
    print(f"  2. Cambiar RAG_CHUNK_SIZE y RAG_CHUNK_OVERLAP en .env")
    print(f"  3. Ejecutar: POST /models/rag/index (para reindexar)")
    print(f"  4. Ejecutar diagnostico_rag_mejorado.py nuevamente")
    print(f"  5. Comparar métricas de retrieval (precision, recall, F1)")
    print(f"  6. Seleccionar mejor configuración basada en resultados")


if __name__ == "__main__":
    try:
        stats = analyze_chunking()
        suggest_optimizations()
        print("\n✓ Análisis completado.")
    except Exception as exc:
        print(f"\n❌ Error: {exc}")
        import traceback
        traceback.print_exc()
