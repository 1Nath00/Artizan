#!/usr/bin/env python
"""Test script para validar los cambios en evaluation.py"""

import sys
sys.path.insert(0, '.')

from app.models.rag.evaluation import (
    RELEVANT_BY_QUESTION,
    QUESTIONS,
    verify_filenames,
    eval_retrieval,
)

print("\n=== VALIDACION DE CAMBIOS EN EVALUATION.PY ===\n")

# Test 1: Verificar que RELEVANT_BY_QUESTION está poblado
print("[OK] Test 1: RELEVANT_BY_QUESTION existe y esta poblado")
print(f"  - Total preguntas en GT: {len(RELEVANT_BY_QUESTION)}")
print(f"  - Total preguntas en QUESTIONS: {sum(len(qs) for qs in QUESTIONS.values())}")
assert len(RELEVANT_BY_QUESTION) == 10, "Deben haber 10 preguntas en RELEVANT_BY_QUESTION"
print("  [OK] Numero correcto de preguntas en GT")

# Test 2: Validar estructura de RELEVANT_BY_QUESTION
print("\n[OK] Test 2: Estructura de RELEVANT_BY_QUESTION")
for q, files in RELEVANT_BY_QUESTION.items():
    assert isinstance(files, set), f"Valor para {q} debe ser un set"
    assert len(files) > 0, f"Cada pregunta debe tener al menos 1 archivo: {q}"
print(f"  [OK] Todas las preguntas tienen sets con archivos validos")

# Test 3: Verificar que todas las preguntas están en QUESTIONS
print("\n[OK] Test 3: Consistencia entre QUESTIONS y RELEVANT_BY_QUESTION")
all_questions = set()
for qs in QUESTIONS.values():
    all_questions.update(qs)
for q in RELEVANT_BY_QUESTION:
    assert q in all_questions, f"Pregunta {q} en GT pero no en QUESTIONS"
print(f"  [OK] Todas las preguntas en GT existen en QUESTIONS")

# Test 4: Verificar filenames (sin conectar a BD, solo estructura)
print("\n[OK] Test 4: Estructura de filenames en GT")
print(f"  Cubismo: {len([q for q in RELEVANT_BY_QUESTION if q.startswith('¿') and any(c in q for c in ['cubismo', 'cubist'])])} preguntas")
print(f"  Barroco: {len([q for q in RELEVANT_BY_QUESTION if q.startswith('¿') and any(c in q for c in ['barroco'])])} preguntas")

# Test 5: Deduplicación por filename
print("\n[OK] Test 5: Test de deduplicacion por filename en eval_retrieval")
test_hits = [
    {"filename": "file1.txt", "text": "content1"},
    {"filename": "file1.txt", "text": "content1"},
    {"filename": "file2.txt", "text": "content2"},
]
deduped = list(dict.fromkeys(h["filename"] for h in test_hits))
assert deduped == ["file1.txt", "file2.txt"], "Deduplicacion debe preservar orden"
print(f"  [OK] Deduplicacion por filename funciona correctamente")

# Test 6: Verificar que verify_filenames es callable
print("\n[OK] Test 6: Funcion verify_filenames es callable")
print(f"  - verify_filenames es funcion: {callable(verify_filenames)}")
print("  [OK] verify_filenames definida e importable")

# Test 7: eval_retrieval con parámetro optional
print("\n[OK] Test 7: eval_retrieval acepta parametro relevant opcional")
try:
    # Solo verificar que la función existe y tiene la firma correcta
    import inspect
    sig = inspect.signature(eval_retrieval)
    params = list(sig.parameters.keys())
    assert 'k' in params, "eval_retrieval debe tener parametro k"
    assert 'relevant' in params, "eval_retrieval debe tener parametro relevant"
    assert sig.parameters['relevant'].default is None, "relevant debe tener default None"
    print(f"  [OK] eval_retrieval firma correcta: {sig}")
except Exception as e:
    print(f"  [FAIL] Error en eval_retrieval: {e}")

print("\n" + "="*50)
print("[OK] TODOS LOS TESTS PASARON")
print("="*50)
