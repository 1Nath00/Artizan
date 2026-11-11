"""
Script para probar diferentes valores de K y comparar resultados.
Mide latencia, retrieval quality y generación.
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

from app import config
from app.models.rag import service, evaluation


def test_k_values():
    """Test retrieval with multiple K values."""
    
    k_values = [1, 3, 5, 8, 10, 12, 15, 20]
    test_questions = [
        "¿Qué es el cubismo?",
        "¿Cuáles son las características del cubismo?",
        "¿Qué es el barroco?",
    ]
    
    output_file = Path("test_k_results.csv")
    results = []
    
    print("=" * 80)
    print("PRUEBA DE VALORES K")
    print("=" * 80)
    
    for question in test_questions:
        print(f"\nPregunta: {question}")
        print("-" * 80)
        
        for k in k_values:
            t0 = time.time()
            try:
                hits = service.retrieve(question, k=k, use_deduplication=False)
                elapsed = time.time() - t0
                
                unique_docs = len(set(h["filename"] for h in hits))
                avg_distance = sum(h.get("distance", 0) for h in hits) / len(hits) if hits else 0
                
                result = {
                    "question": question,
                    "k": k,
                    "hits_found": len(hits),
                    "unique_documents": unique_docs,
                    "avg_distance": round(avg_distance, 4),
                    "retrieval_time_ms": round(elapsed * 1000, 1),
                }
                
                results.append(result)
                
                print(f"  K={k:2d} | Hits: {len(hits):2d} | Docs: {unique_docs} | "
                      f"Dist: {avg_distance:.4f} | Time: {elapsed*1000:.1f}ms")
                
            except Exception as exc:
                print(f"  K={k:2d} | ERROR: {exc}")
                results.append({
                    "question": question,
                    "k": k,
                    "error": str(exc)
                })
    
    # Write results to CSV
    if results and "error" not in results[0]:
        with output_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        print(f"\nResultados guardados en: {output_file}")
    
    return results


def test_deduplication():
    """Test the effect of deduplication."""
    
    test_questions = [
        "¿Qué es el cubismo?",
        "¿Qué es el barroco?",
    ]
    
    print("\n" + "=" * 80)
    print("PRUEBA DE DEDUPLICACIÓN")
    print("=" * 80)
    
    results = []
    
    for question in test_questions:
        print(f"\nPregunta: {question}")
        
        for use_dedup in [False, True]:
            dedup_label = "con dedup" if use_dedup else "sin dedup"
            
            hits = service.retrieve(question, k=10, use_deduplication=use_dedup)
            
            from app.models.rag.retrieval_optimizations import analyze_chunks
            stats = analyze_chunks(hits)
            
            result = {
                "question": question,
                "deduplication": dedup_label,
                "hits_count": stats["cantidad_chunks"],
                "unique_chunks": stats["chunks_unicos"],
                "duplication_rate": f"{stats['tasa_duplicacion']:.1f}%",
                "avg_length": stats["promedio_longitud"],
                "unique_documents": stats["documentos_unicos"],
            }
            
            results.append(result)
            
            print(f"  {dedup_label:15s} | "
                  f"Total: {stats['cantidad_chunks']:2d} | "
                  f"Únicos: {stats['chunks_unicos']:2d} | "
                  f"Dup: {stats['tasa_duplicacion']:5.1f}% | "
                  f"Docs: {stats['documentos_unicos']}")
    
    return results


def test_generation_quality():
    """Test generation quality with improved prompt."""
    
    test_cases = [
        {
            "question": "¿Qué es el cubismo?",
            "k": 10,
        },
        {
            "question": "¿Cuáles son las características del barroco?",
            "k": 10,
        },
    ]
    
    print("\n" + "=" * 80)
    print("PRUEBA DE CALIDAD DE GENERACIÓN")
    print("=" * 80)
    
    results = []
    
    for test_case in test_cases:
        question = test_case["question"]
        k = test_case["k"]
        
        print(f"\nPregunta: {question}")
        print(f"K = {k}")
        print("-" * 80)
        
        try:
            t0 = time.time()
            result = service.ask(question, k=k)
            elapsed = time.time() - t0
            
            answer = result["answer"]
            sources_count = len(result["sources"])
            
            # Extract citations
            from app.models.rag.generation_improvements import extract_citations, validate_citations
            citations = extract_citations(answer)
            citation_stats = validate_citations(answer, sources_count)
            
            # Count response stats
            words = len(answer.split())
            sentences = len([s for s in answer.split(".") if s.strip()])
            
            result_record = {
                "question": question,
                "k": k,
                "answer_length_words": words,
                "sentence_count": sentences,
                "total_citations": citation_stats["total_citations"],
                "unique_citations": citation_stats["unique_citations"],
                "coverage_percent": f"{citation_stats['coverage']:.1f}%",
                "generation_time_ms": round(elapsed * 1000, 1),
            }
            
            results.append(result_record)
            
            print(f"Respuesta (primeras 150 caracteres):")
            print(f"  {answer[:150]}...")
            print(f"\nEstadísticas:")
            print(f"  Palabras: {words}")
            print(f"  Oraciones: {sentences}")
            print(f"  Citas totales: {citation_stats['total_citations']}")
            print(f"  Citas únicas: {citation_stats['unique_citations']}")
            print(f"  Cobertura: {citation_stats['coverage']:.1f}%")
            print(f"  Tiempo: {elapsed:.2f}s")
            
            if citation_stats["invalid_citations"]:
                print(f"  ⚠️  Citas inválidas: {citation_stats['invalid_citations']}")
            
        except Exception as exc:
            print(f"ERROR: {exc}")
            results.append({
                "question": question,
                "error": str(exc)
            })
    
    return results


if __name__ == "__main__":
    print("\nIniciando pruebas del sistema RAG mejorado...\n")
    
    try:
        k_results = test_k_values()
        dedup_results = test_deduplication()
        gen_results = test_generation_quality()
        
        print("\n" + "=" * 80)
        print("RESUMEN DE PRUEBAS")
        print("=" * 80)
        print(f"✓ Pruebas de K: {len(k_results)} resultados")
        print(f"✓ Deduplicación: {len(dedup_results)} resultados")
        print(f"✓ Generación: {len(gen_results)} resultados")
        
    except Exception as exc:
        print(f"\n❌ Error durante las pruebas: {exc}")
        import traceback
        traceback.print_exc()
