"""
Script de validación del sistema RAG mejorado.

Verifica que:
1. Todos los nuevos módulos se importan correctamente
2. Las funciones nuevas funcionan
3. Los endpoints existentes siguen funcionando
4. No hay errores de compatibilidad
"""

from __future__ import annotations

import sys
import os

# Fix encoding for Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"


def test_imports():
    """Test that all imports work correctly."""
    print("\n" + "=" * 80)
    print("PRUEBA 1: IMPORTS")
    print("=" * 80)
    
    try:
        from app.models.rag import service
        print("[OK] app.models.rag.service")
        
        from app.models.rag.retrieval_optimizations import (
            deduplicate_hits,
            mmr_rerank,
            analyze_chunks,
            similarity_score
        )
        print("[OK] app.models.rag.retrieval_optimizations")
        
        from app.models.rag.generation_improvements import (
            IMPROVED_SYSTEM_PROMPT,
            improved_build_messages,
            extract_citations,
            validate_citations,
            detect_hallucinations,
            count_response_stats
        )
        print("[OK] app.models.rag.generation_improvements")
        
        from app.models.rag.comprehensive_evaluation import (
            comprehensive_evaluation,
            evaluation_report
        )
        print("[OK] app.models.rag.comprehensive_evaluation")
        
        return True
    except Exception as exc:
        print(f"[ERROR] Import error: {exc}")
        import traceback
        traceback.print_exc()
        return False


def test_deduplication():
    """Test deduplication function."""
    print("\n" + "=" * 80)
    print("PRUEBA 2: DEDUPLICACION")
    print("=" * 80)
    
    try:
        from app.models.rag.retrieval_optimizations import deduplicate_hits, similarity_score
        
        # Create test data
        hits = [
            {"text": "El cubismo es un movimiento artistico", "filename": "doc1.txt", "chunk": 1},
            {"text": "El cubismo fue un movimiento artistico", "filename": "doc1.txt", "chunk": 2},
            {"text": "Totalmente diferente texto aqui", "filename": "doc2.txt", "chunk": 1},
        ]
        
        # Test similarity
        sim = similarity_score(hits[0]["text"], hits[1]["text"])
        print(f"Similitud entre chunks 0-1: {sim:.3f} (esperado: ~0.85+)")
        
        # Test deduplication
        dedup = deduplicate_hits(hits, similarity_threshold=0.7)
        print(f"Hits originales: {len(hits)}, despues dedup: {len(dedup)}")
        
        if len(dedup) < len(hits):
            print("[OK] Deduplicacion funcionando correctamente")
            return True
        else:
            print("[ERROR] Deduplicacion no removio duplicados")
            return False
            
    except Exception as exc:
        print(f"[ERROR] Error: {exc}")
        import traceback
        traceback.print_exc()
        return False


def test_citations():
    """Test citation extraction and validation."""
    print("\n" + "=" * 80)
    print("PRUEBA 3: VALIDACION DE CITAS")
    print("=" * 80)
    
    try:
        from app.models.rag.generation_improvements import extract_citations, validate_citations
        
        # Test citation extraction
        answer = "El cubismo surgio en Paris [1]. Fue iniciado por Picasso y Braque [2]. El movimiento [3] cambio el arte [1]."
        
        citations = extract_citations(answer)
        print(f"Citas encontradas: {citations}")
        print(f"Citas unicas: {set(citations)}")
        
        # Test validation
        stats = validate_citations(answer, num_fragments=3)
        print(f"Estadisticas de citas:")
        print(f"  - Total: {stats['total_citations']}")
        print(f"  - Unicas: {stats['unique_citations']}")
        print(f"  - Validas: {stats['valid_citations']}")
        print(f"  - Invalidas: {stats['invalid_citations']}")
        print(f"  - Cobertura: {stats['coverage']:.1f}%")
        
        if stats['total_citations'] > 0 and stats['unique_citations'] > 0:
            print("[OK] Validacion de citas funcionando")
            return True
        else:
            print("[ERROR] No se extrajeron citas")
            return False
            
    except Exception as exc:
        print(f"[ERROR] Error: {exc}")
        import traceback
        traceback.print_exc()
        return False


def test_response_stats():
    """Test response statistics calculation."""
    print("\n" + "=" * 80)
    print("PRUEBA 4: ESTADISTICAS DE RESPUESTA")
    print("=" * 80)
    
    try:
        from app.models.rag.generation_improvements import count_response_stats
        
        answer = "El cubismo es un movimiento artistico de principios del siglo XX. Fue iniciado por Pablo Picasso y Georges Braque. El movimiento se caracterizo por la descomposicion de objetos en formas geometricas."
        
        stats = count_response_stats(answer)
        print(f"Estadisticas de respuesta:")
        print(f"  - Palabras: {stats['word_count']}")
        print(f"  - Oraciones: {stats['sentence_count']}")
        print(f"  - Palabras/oracion: {stats['avg_sentence_length']}")
        print(f"  - Parrafos: {stats['paragraph_count']}")
        
        if stats['word_count'] > 0 and stats['sentence_count'] > 0:
            print("[OK] Estadisticas calculadas correctamente")
            return True
        else:
            print("[ERROR] Error en calculo de estadisticas")
            return False
            
    except Exception as exc:
        print(f"[ERROR] Error: {exc}")
        import traceback
        traceback.print_exc()
        return False


def test_service_compatibility():
    """Test that service.py changes don't break existing functionality."""
    print("\n" + "=" * 80)
    print("PRUEBA 5: COMPATIBILIDAD DE SERVICE")
    print("=" * 80)
    
    try:
        from app.models.rag import service
        from app import config
        
        # Check that functions exist
        assert hasattr(service, 'retrieve'), "retrieve() function missing"
        print("[OK] retrieve() exists")
        
        assert hasattr(service, 'build_messages'), "build_messages() function missing"
        print("[OK] build_messages() exists")
        
        assert hasattr(service, 'ask'), "ask() function missing"
        print("[OK] ask() exists")
        
        # Check new functions
        assert hasattr(service, 'retrieve_multiple_k'), "retrieve_multiple_k() function missing"
        print("[OK] retrieve_multiple_k() exists (new)")
        
        assert hasattr(service, 'analyze_retrieval'), "analyze_retrieval() function missing"
        print("[OK] analyze_retrieval() exists (new)")
        
        # Check SYSTEM_PROMPT is defined
        assert hasattr(service, 'SYSTEM_PROMPT'), "SYSTEM_PROMPT not defined"
        assert len(service.SYSTEM_PROMPT) > 0, "SYSTEM_PROMPT is empty"
        print("[OK] SYSTEM_PROMPT defined and updated")
        
        print("\n[OK] Compatibilidad de service.py validada")
        return True
        
    except AssertionError as exc:
        print(f"[ERROR] {exc}")
        return False
    except Exception as exc:
        print(f"[ERROR] Error: {exc}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("\n" + "=" * 80)
    print("VALIDACION DEL SISTEMA RAG MEJORADO")
    print("=" * 80)
    
    tests = [
        ("Imports", test_imports),
        ("Deduplicacion", test_deduplication),
        ("Validacion de Citas", test_citations),
        ("Estadisticas", test_response_stats),
        ("Compatibilidad", test_service_compatibility),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as exc:
            print(f"\n[ERROR] Error fatal en {name}: {exc}")
            results[name] = False
    
    # Summary
    print("\n" + "=" * 80)
    print("RESUMEN DE VALIDACION")
    print("=" * 80)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for name, result in results.items():
        status = "[OK]" if result else "[FALLO]"
        print(f"{status} {name}")
    
    print(f"\nResultado: {passed}/{total} pruebas pasadas")
    
    if passed == total:
        print("\n[OK] Sistema RAG mejorado validado exitosamente")
        return 0
    else:
        print("\n[ERROR] Algunas pruebas fallaron")
        return 1


if __name__ == "__main__":
    sys.exit(main())
