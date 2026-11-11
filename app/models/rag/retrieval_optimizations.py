"""
Optimizaciones avanzadas de recuperación para RAG.

Incluye:
- Maximal Marginal Relevance (MMR) para diversidad
- Deduplicación de chunks similares
- Reranking mejorado
- Análisis de chunks
"""

from __future__ import annotations

import math
import unicodedata
from typing import Any


def normalize_text(text: str) -> str:
    """Normaliza texto para comparación (minúsculas, sin diacríticos)."""
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn").strip()


def similarity_score(text1: str, text2: str) -> float:
    """
    Calcula similitud simple entre dos textos usando tokens compartidos.
    Rango: [0, 1], donde 1 es idéntico.
    """
    norm1 = set(normalize_text(text1).split())
    norm2 = set(normalize_text(text2).split())
    
    if not norm1 or not norm2:
        return 0.0
    
    intersection = len(norm1 & norm2)
    union = len(norm1 | norm2)
    
    # Jaccard similarity
    return intersection / union if union > 0 else 0.0


def deduplicate_hits(
    hits: list[dict[str, Any]], 
    similarity_threshold: float = 0.7
) -> list[dict[str, Any]]:
    """
    Elimina chunks duplicados o muy similares.
    Mantiene el primero (más relevante por ranking) y descarta los siguientes similares.
    
    Args:
        hits: Lista de chunks recuperados
        similarity_threshold: Umbral de similitud (0-1) para considerar duplicado
    
    Returns:
        Lista de chunks deduplicados
    """
    if not hits:
        return []
    
    deduplicated = []
    seen_texts = []
    
    for hit in hits:
        text = hit.get("text", "")
        is_duplicate = False
        
        # Comparar con todos los textos ya agregados
        for seen_text in seen_texts:
            score = similarity_score(text, seen_text)
            if score >= similarity_threshold:
                is_duplicate = True
                break
        
        if not is_duplicate:
            deduplicated.append(hit)
            seen_texts.append(text)
    
    return deduplicated


def mmr_rerank(
    hits: list[dict[str, Any]],
    query_embedding: list[float],
    embeddings: list[list[float]],
    diversity_weight: float = 0.5,
    k: int | None = None
) -> list[dict[str, Any]]:
    """
    Rerank usando Maximal Marginal Relevance (MMR).
    Balancea relevancia (similitud con query) y diversidad (diferencia con seleccionados).
    
    MMR = λ * (similitud_query) - (1 - λ) * (similitud_máxima_con_seleccionados)
    
    Args:
        hits: Lista de chunks recuperados
        query_embedding: Embedding de la pregunta
        embeddings: Lista de embeddings de los chunks
        diversity_weight: Peso de la diversidad (1 - relevancia). Rango: [0, 1]
        k: Si se proporciona, retorna solo los top-k después del reranking
    
    Returns:
        Lista de chunks rerankeados
    """
    if not hits or not embeddings:
        return hits
    
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        """Calcula similitud coseno entre dos vectores."""
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    # Calcular similitud de cada chunk con la query
    relevance_scores = [
        cosine_similarity(query_embedding, emb)
        for emb in embeddings
    ]
    
    # Inicializar: el más relevante es siempre seleccionado primero
    selected_indices = []
    remaining_indices = list(range(len(hits)))
    
    if remaining_indices:
        # Seleccionar el primer chunk (más relevante por similitud vectorial)
        best_idx = max(remaining_indices, key=lambda i: relevance_scores[i])
        selected_indices.append(best_idx)
        remaining_indices.remove(best_idx)
    
    # Seleccionar el resto iterativamente usando MMR
    while remaining_indices:
        mmr_scores = []
        
        for idx in remaining_indices:
            # Similitud con la query
            rel_score = relevance_scores[idx]
            
            # Similitud máxima con chunks ya seleccionados
            max_similarity_with_selected = 0.0
            for selected_idx in selected_indices:
                sim = cosine_similarity(embeddings[idx], embeddings[selected_idx])
                max_similarity_with_selected = max(max_similarity_with_selected, sim)
            
            # MMR = λ * relevancia - (1 - λ) * similitud_máxima
            mmr_score = (
                diversity_weight * rel_score - 
                (1 - diversity_weight) * max_similarity_with_selected
            )
            mmr_scores.append((mmr_score, idx))
        
        # Seleccionar el chunk con mejor MMR
        if mmr_scores:
            _, best_idx = max(mmr_scores)
            selected_indices.append(best_idx)
            remaining_indices.remove(best_idx)
    
    # Reordenar hits según selected_indices
    reranked = [hits[i] for i in selected_indices]
    
    # Retornar solo top-k si se especifica
    if k is not None:
        return reranked[:k]
    
    return reranked


def analyze_chunks(hits: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Analiza características de los chunks recuperados.
    
    Retorna:
        - cantidad_chunks: Número total de chunks
        - chunks_unicos: Chunks deduplicados (threshold 0.7)
        - tasa_duplicacion: Porcentaje de duplicados
        - promedio_longitud: Caracteres promedio
        - documentos_unicos: Cantidad de documentos diferentes
        - distancia_promedio: Similitud promedio con query
    """
    if not hits:
        return {
            "cantidad_chunks": 0,
            "chunks_unicos": 0,
            "tasa_duplicacion": 0.0,
            "promedio_longitud": 0,
            "documentos_unicos": 0,
            "distancia_promedio": 0.0,
        }
    
    unique_hits = deduplicate_hits(hits, similarity_threshold=0.7)
    
    return {
        "cantidad_chunks": len(hits),
        "chunks_unicos": len(unique_hits),
        "tasa_duplicacion": 100.0 * (len(hits) - len(unique_hits)) / len(hits),
        "promedio_longitud": sum(len(h.get("text", "")) for h in hits) // len(hits),
        "documentos_unicos": len(set(h.get("filename", "") for h in hits)),
        "distancia_promedio": sum(h.get("distance", 0) for h in hits) / len(hits),
    }
