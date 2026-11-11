"""
Diagnóstico integral del RAG mejorado.

Ejecuta las mismas pruebas que el diagnóstico anterior pero con:
- Sistema de generación mejorado
- Deduplicación
- Análisis de latencia
- Comparación automática antes/después
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any

from app import config
from app.models.rag import evaluation, service
from app.models.rag.comprehensive_evaluation import comprehensive_evaluation, evaluation_report


# Test questions (same as evaluation.py)
TEST_QUESTIONS = {
    "cubismo": [
        "¿Qué es el cubismo?",
        "Define el cubismo como movimiento artístico.",
        "¿Cuáles son las características del cubismo?",
        "¿Quiénes fundaron el cubismo y cuándo surgió?",
        "¿En qué consiste la representación cubista de los objetos?",
    ],
    "barroco": [
        "¿Qué es el barroco?",
        "Define el arte barroco.",
        "¿Cuáles son las características del barroco?",
        "¿Cuándo surgió el barroco y qué lo caracteriza?",
        "¿Qué significa el término barroco?",
    ],
}


def run_comprehensive_diagnostics():
    """Run comprehensive evaluation of the improved RAG system."""
    
    print("\n" + "=" * 100)
    print("DIAGNÓSTICO INTEGRAL DEL SISTEMA RAG MEJORADO")
    print("=" * 100)
    print(f"Configuración:")
    print(f"  - Embedding model: {config.RAG_EMBEDDING_MODEL}")
    print(f"  - LLM model: {config.RAG_LLM_MODEL}")
    print(f"  - Chunk size: {config.RAG_CHUNK_SIZE}")
    print(f"  - Chunk overlap: {config.RAG_CHUNK_OVERLAP}")
    print(f"  - Top-K (default): {config.RAG_TOP_K}")
    print()
    
    # Collect all evaluation results
    all_evaluations = []
    
    for topic, questions in TEST_QUESTIONS.items():
        print(f"\n{'=' * 100}")
        print(f"TEMA: {topic.upper()}")
        print(f"{'=' * 100}")
        
        for i, question in enumerate(questions, 1):
            print(f"\n[{i}/{len(questions)}] {question}")
            print("-" * 100)
            
            try:
                # Run comprehensive evaluation
                result = comprehensive_evaluation(question, k=10)
                all_evaluations.append({
                    "topic": topic,
                    "question": question,
                    "index": i,
                    **result
                })
                
                # Print quick summary
                if "error" not in result.get("generation", {}):
                    retrieval = result["retrieval"]
                    generation = result["generation"]
                    citations = result["citations"]
                    latency = result["latency"]
                    
                    print(f"  ✓ Recuperación:")
                    print(f"    - Chunks: {retrieval.get('hits_count', 'N/A')}")
                    print(f"    - Documentos únicos: {retrieval.get('unique_documents', 'N/A')}")
                    print(f"    - Duplicados removidos: {retrieval.get('duplicates_removed', 'N/A')}")
                    
                    print(f"  ✓ Generación:")
                    print(f"    - Palabras: {generation.get('word_count', 'N/A')}")
                    print(f"    - Oraciones: {generation.get('sentence_count', 'N/A')}")
                    
                    print(f"  ✓ Citas:")
                    print(f"    - Total: {citations.get('total_citations', 'N/A')}")
                    print(f"    - Únicas: {citations.get('unique_citations', 'N/A')}")
                    print(f"    - Cobertura: {result['integrated'].get('chunk_coverage', 0):.1f}%")
                    if citations.get("invalid_citations", 0) > 0:
                        print(f"    - ⚠️  Citas inválidas: {citations.get('invalid_citations', 0)}")
                    
                    print(f"  ✓ Latencia:")
                    print(f"    - Recuperación: {latency.get('retrieval_ms', 'N/A')}ms")
                    print(f"    - Generación: {latency.get('generation_ms', 'N/A')}ms")
                    print(f"    - Total: {latency.get('total_ms', 'N/A')}ms")
                else:
                    print(f"  ✗ Error: {result['generation']['error']}")
                    
            except Exception as exc:
                print(f"  ✗ Excepción: {type(exc).__name__}: {exc}")
                all_evaluations.append({
                    "topic": topic,
                    "question": question,
                    "index": i,
                    "error": str(exc)
                })
    
    # Print comprehensive report
    evaluation_report(all_evaluations)
    
    # Save results to JSON
    results_file = Path("diagnostico_mejorado.jsonl")
    with results_file.open("w", encoding="utf-8") as f:
        for eval_result in all_evaluations:
            f.write(json.dumps(eval_result, ensure_ascii=False) + "\n")
    
    print(f"\n✓ Resultados guardados en: {results_file}")
    
    # Generate comparison CSV
    generate_comparison_csv(all_evaluations)
    
    return all_evaluations


def generate_comparison_csv(evaluations: list[dict[str, Any]]) -> None:
    """Generate a CSV with before/after comparison."""
    
    output_file = Path("diagnostico_comparacion.csv")
    
    rows = []
    for eval_result in evaluations:
        if "error" in eval_result:
            continue
        
        row = {
            "topic": eval_result.get("topic", ""),
            "question": eval_result.get("question", ""),
            "k": eval_result.get("k", ""),
            
            # Retrieval
            "retrieval_hits": eval_result["retrieval"].get("hits_count", ""),
            "retrieval_docs": eval_result["retrieval"].get("unique_documents", ""),
            "retrieval_dup_rate": f"{eval_result['retrieval'].get('duplicate_rate', 0):.1f}%",
            
            # Generation
            "gen_word_count": eval_result["generation"].get("word_count", ""),
            "gen_sentence_count": eval_result["generation"].get("sentence_count", ""),
            
            # Citations
            "cites_total": eval_result["citations"].get("total_citations", ""),
            "cites_unique": eval_result["citations"].get("unique_citations", ""),
            "cites_coverage": f"{eval_result['integrated'].get('chunk_coverage', 0):.1f}%",
            "cites_invalid": eval_result["citations"].get("invalid_citations", ""),
            
            # Latency
            "latency_retrieval_ms": eval_result["latency"].get("retrieval_ms", ""),
            "latency_generation_ms": eval_result["latency"].get("generation_ms", ""),
            "latency_total_ms": eval_result["latency"].get("total_ms", ""),
        }
        rows.append(row)
    
    if rows:
        with output_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"✓ Comparación guardada en: {output_file}")


def compare_with_baseline():
    """Compare current results with baseline (diagnostico_antes.csv)."""
    
    baseline_file = Path("diagnostico_antes.csv")
    
    if not baseline_file.exists():
        print("⚠️  No baseline file found. Skipping comparison.")
        return
    
    print("\n" + "=" * 100)
    print("COMPARACIÓN CON LÍNEA BASE")
    print("=" * 100)
    
    # Load baseline
    baseline_rows = {}
    with baseline_file.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            baseline_rows[row.get("id", "")] = row
    
    # Read improved results
    improved_file = Path("diagnostico_comparacion.csv")
    if not improved_file.exists():
        print("⚠️  Improved results file not found.")
        return
    
    improved_rows = {}
    with improved_file.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            question = row.get("question", "")
            improved_rows[question] = row
    
    print("\n| Pregunta | K | Hits Antes | Hits Después | Palabras Antes | Palabras Después | Latencia Antes | Latencia Después |")
    print("|---|---|---|---|---|---|---|---|")
    
    for question, improved in improved_rows.items():
        # Find matching baseline
        baseline = None
        for b_row in baseline_rows.values():
            if question in b_row.get("pregunta", ""):
                baseline = b_row
                break
        
        if baseline:
            # Extract metrics
            hits_before = baseline.get("chunks_top10", "?")
            hits_after = improved.get("retrieval_hits", "?")
            
            words_before = "?"  # Not in baseline
            words_after = improved.get("gen_word_count", "?")
            
            latency_before = baseline.get("latencia_ms", "?")
            latency_after = improved.get("latency_total_ms", "?")
            
            print(f"| {question[:40]:<40} | 10 | {hits_before:<10} | {hits_after:<12} | {words_before:<14} | {words_after:<16} | {latency_before:<14} | {latency_after:<16} |")


if __name__ == "__main__":
    try:
        evaluations = run_comprehensive_diagnostics()
        compare_with_baseline()
        print("\n✓ Diagnóstico completado exitosamente.")
    except Exception as exc:
        print(f"\n❌ Error en el diagnóstico: {exc}")
        import traceback
        traceback.print_exc()
