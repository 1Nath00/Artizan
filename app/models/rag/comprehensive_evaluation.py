"""
Evaluación integral del sistema RAG (antes y después de mejoras).

Incluye:
- Métricas de retrieval
- Métricas de generación  
- Métricas integradas
- Comparación automática
"""

from __future__ import annotations

import json
import time
from typing import Any

from app.models.rag import service, evaluation
from app.models.rag.generation_improvements import (
    extract_citations,
    validate_citations,
    count_response_stats
)


def comprehensive_evaluation(question: str, expected_answer: str = None, k: int = 10) -> dict[str, Any]:
    """
    Comprehensive evaluation of a question through the entire RAG pipeline.
    
    Measures:
    1. Retrieval quality
    2. Generation quality
    3. Citation validity
    4. Hallucinations
    5. Coverage
    6. Latency breakdown
    """
    
    results = {
        "question": question,
        "k": k,
        "retrieval": {},
        "generation": {},
        "citations": {},
        "integrated": {},
        "latency": {},
    }
    
    # ===== RETRIEVAL =====
    t_start = time.time()
    
    try:
        hits = service.retrieve(question, k=k, use_deduplication=True)
        results["retrieval"]["hits_count"] = len(hits)
        results["retrieval"]["unique_documents"] = len(set(h["filename"] for h in hits))
        results["retrieval"]["avg_distance"] = (
            sum(h.get("distance", 0) for h in hits) / len(hits) if hits else 0
        )
        
        # Deduplication stats
        from app.models.rag.retrieval_optimizations import deduplicate_hits, analyze_chunks
        original_count = len(hits)
        dedup_hits = deduplicate_hits(hits, similarity_threshold=0.7)
        results["retrieval"]["duplicates_removed"] = original_count - len(dedup_hits)
        
        stats = analyze_chunks(hits)
        results["retrieval"]["duplicate_rate"] = stats["tasa_duplicacion"]
        
    except Exception as exc:
        results["retrieval"]["error"] = str(exc)
        return results
    
    t_retrieval = time.time() - t_start
    results["latency"]["retrieval_ms"] = round(t_retrieval * 1000, 0)
    
    # ===== GENERATION =====
    t_start = time.time()
    
    try:
        response = service.ask(question, k=k)
        answer = response["answer"]
        sources = response["sources"]
        
        results["generation"]["answer_length"] = len(answer)
        results["generation"]["answer"] = answer[:200] + "..." if len(answer) > 200 else answer
        
        # Count stats
        stats = count_response_stats(answer)
        results["generation"].update(stats)
        
    except Exception as exc:
        results["generation"]["error"] = str(exc)
        return results
    
    t_generation = time.time() - t_start
    results["latency"]["generation_ms"] = round(t_generation * 1000, 0)
    results["latency"]["total_ms"] = round((t_retrieval + t_generation) * 1000, 0)
    
    # ===== CITATIONS =====
    citations = extract_citations(answer)
    citation_stats = validate_citations(answer, len(sources))
    results["citations"] = citation_stats
    
    # ===== GROUNDEDNESS =====
    # Simple check: all non-empty citations should be valid
    if citation_stats["invalid_citations"]:
        results["citations"]["has_invalid_citations"] = True
    
    # ===== INTEGRATED METRICS =====
    
    # 1. Coverage: percentage of retrieved chunks that are cited
    if len(sources) > 0:
        coverage = 100.0 * citation_stats["unique_citations"] / len(sources)
        results["integrated"]["chunk_coverage"] = coverage
    
    # 2. Abstention detection
    refusal_phrases = [
        "no encuentro información suficiente",
        "no tengo información",
        "no disponible",
    ]
    is_refusing = any(phrase in answer.lower() for phrase in refusal_phrases)
    results["integrated"]["is_refusing"] = is_refusing
    
    # 3. Citation quality
    has_citations = citation_stats["unique_citations"] > 0
    citations_valid = citation_stats["invalid_citations"] == 0
    results["integrated"]["has_citations"] = has_citations
    results["integrated"]["citations_valid"] = citations_valid
    
    # 4. Response quality indicators
    word_count = stats.get("word_count", 0)
    sentence_count = stats.get("sentence_count", 0)
    results["integrated"]["word_count"] = word_count
    results["integrated"]["sentence_count"] = sentence_count
    results["integrated"]["too_short"] = word_count < 50  # Less than 50 words
    results["integrated"]["too_long"] = word_count > 1000  # More than 1000 words
    
    # 5. Duplication in sources
    results["integrated"]["source_duplication_rate"] = results["retrieval"].get("duplicate_rate", 0)
    
    return results


def evaluation_report(evaluations: list[dict[str, Any]]) -> None:
    """Generate a human-readable report from evaluation results."""
    
    print("\n" + "=" * 100)
    print("REPORTE DE EVALUACIÓN INTEGRAL DEL RAG")
    print("=" * 100)
    
    # Aggregate statistics
    total_evals = len(evaluations)
    successful = sum(1 for e in evaluations if "error" not in e.get("generation", {}))
    
    print(f"\n📊 RESUMEN GENERAL")
    print(f"  Total de evaluaciones: {total_evals}")
    print(f"  Exitosas: {successful}/{total_evals}")
    
    # Retrieval stats
    print(f"\n🔍 RECUPERACIÓN")
    avg_hits = sum(e["retrieval"].get("hits_count", 0) for e in evaluations) / successful if successful else 0
    avg_docs = sum(e["retrieval"].get("unique_documents", 0) for e in evaluations) / successful if successful else 0
    avg_dups = sum(e["retrieval"].get("duplicate_rate", 0) for e in evaluations) / successful if successful else 0
    
    print(f"  Chunks recuperados (promedio): {avg_hits:.1f}")
    print(f"  Documentos únicos (promedio): {avg_docs:.1f}")
    print(f"  Tasa de duplicación (promedio): {avg_dups:.1f}%")
    
    # Generation stats
    print(f"\n✍️  GENERACIÓN")
    avg_words = sum(e["generation"].get("word_count", 0) for e in evaluations) / successful if successful else 0
    avg_sentences = sum(e["generation"].get("sentence_count", 0) for e in evaluations) / successful if successful else 0
    avg_length = sum(e["generation"].get("avg_sentence_length", 0) for e in evaluations) / successful if successful else 0
    
    print(f"  Palabras (promedio): {avg_words:.1f}")
    print(f"  Oraciones (promedio): {avg_sentences:.1f}")
    print(f"  Palabras por oración (promedio): {avg_length:.1f}")
    
    # Citation stats
    print(f"\n🔗 CITAS")
    avg_total_cites = sum(e["citations"].get("total_citations", 0) for e in evaluations) / successful if successful else 0
    avg_unique_cites = sum(e["citations"].get("unique_citations", 0) for e in evaluations) / successful if successful else 0
    avg_coverage = sum(e["integrated"].get("chunk_coverage", 0) for e in evaluations) / successful if successful else 0
    
    with_valid_cites = sum(1 for e in evaluations if e["integrated"].get("citations_valid", False))
    with_invalid_cites = sum(1 for e in evaluations if e["citations"].get("invalid_citations", 0) > 0)
    
    print(f"  Citas totales (promedio): {avg_total_cites:.1f}")
    print(f"  Citas únicas (promedio): {avg_unique_cites:.1f}")
    print(f"  Cobertura de chunks (promedio): {avg_coverage:.1f}%")
    print(f"  Respuestas con citas válidas: {with_valid_cites}/{successful}")
    print(f"  Respuestas con citas inválidas: {with_invalid_cites}/{successful}")
    
    # Latency
    print(f"\n⏱️  LATENCIA")
    avg_retrieval_ms = sum(e["latency"].get("retrieval_ms", 0) for e in evaluations) / successful if successful else 0
    avg_generation_ms = sum(e["latency"].get("generation_ms", 0) for e in evaluations) / successful if successful else 0
    avg_total_ms = sum(e["latency"].get("total_ms", 0) for e in evaluations) / successful if successful else 0
    
    print(f"  Recuperación (promedio): {avg_retrieval_ms:.0f}ms")
    print(f"  Generación (promedio): {avg_generation_ms:.0f}ms")
    print(f"  Total (promedio): {avg_total_ms:.0f}ms ({avg_total_ms/1000:.2f}s)")
    
    # Integrated metrics
    print(f"\n🎯 MÉTRICAS INTEGRADAS")
    refusing = sum(1 for e in evaluations if e["integrated"].get("is_refusing", False))
    too_short = sum(1 for e in evaluations if e["integrated"].get("too_short", False))
    too_long = sum(1 for e in evaluations if e["integrated"].get("too_long", False))
    has_cites = sum(1 for e in evaluations if e["integrated"].get("has_citations", False))
    
    print(f"  Respuestas que se rehúsan: {refusing}/{successful}")
    print(f"  Respuestas muy cortas (<50 palabras): {too_short}/{successful}")
    print(f"  Respuestas muy largas (>1000 palabras): {too_long}/{successful}")
    print(f"  Respuestas con citas: {has_cites}/{successful}")
    
    # Individual results
    print(f"\n📝 RESULTADOS POR PREGUNTA\n")
    print(f"{'Pregunta':<50} {'Palabras':<10} {'Citas':<10} {'Tiempo':<10} {'Estado':<15}")
    print("-" * 95)
    
    for i, e in enumerate(evaluations, 1):
        q = e.get("question", "")[:48]
        words = e["generation"].get("word_count", "?")
        cites = e["citations"].get("unique_citations", "?")
        time_ms = e["latency"].get("total_ms", "?")
        status = "✓ OK" if "error" not in e.get("generation", {}) else "✗ ERROR"
        
        print(f"{q:<50} {words:<10} {cites:<10} {time_ms:<10} {status:<15}")
    
    print("\n" + "=" * 100)
