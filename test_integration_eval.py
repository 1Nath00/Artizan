#!/usr/bin/env python
"""
Script de integración: Demuestra cómo usar el nuevo sistema de evaluación
con RELEVANT_BY_QUESTION.
"""

import sys
sys.path.insert(0, '.')

from app.models.rag.evaluation import (
    RELEVANT_BY_QUESTION,
    QUESTIONS,
    verify_filenames,
    eval_retrieval,
)

print("\nINTEGRACION: EVALUACION DE RETRIEVAL POR PREGUNTA")
print("="*70)

# Paso 1: Validar filenames
print("\n[PASO 1] Validar filenames en el ground truth...")
try:
    missing = verify_filenames()
    if missing:
        print("ERROR: Filenames faltantes en el corpus:")
        for fname, questions in missing.items():
            print(f"  - {repr(fname)} (usado en {len(questions)} preguntas)")
        sys.exit(1)
    else:
        print("[OK] Todos los filenames en RELEVANT_BY_QUESTION existen en el corpus")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Paso 2: Contar preguntas
print("\n[PASO 2] Ground Truth por pregunta")
print("-" * 70)
total_questions = 0
total_gt_docs = 0
for topic, questions in QUESTIONS.items():
    topic_q = len(questions)
    topic_docs = sum(len(RELEVANT_BY_QUESTION.get(q, set())) for q in questions)
    print(f"TEMA: {topic} ({topic_q} preguntas, {topic_docs} GT docs totales)")
    total_questions += topic_q
    total_gt_docs += topic_docs

print(f"\nTotal: {total_questions} preguntas, {total_gt_docs} GT doc-question pairs")

# Paso 3: Detalles de la correccion
print("\n[PASO 3] Cambios aplicados")
print("-" * 70)
print("1. Ground Truth POR PREGUNTA (no por tema)")
print("2. Deduplicacion de filenames en retrieval (dict.fromkeys)")
print("3. Validacion de filenames con verify_filenames()")
print("4. eval_retrieval() usa RELEVANT_BY_QUESTION directamente")
print("5. evaluate_retrieval() llama verify_filenames() antes de evaluar")

print("\n[PASO 4] Capacidades")
print("-" * 70)
print("- verify_filenames(): Valida GT contra corpus (por basename)")
print("- eval_retrieval(k, relevant=None): Evalua por pregunta")
print("- evaluate_retrieval(k=None, sweep=True): Evaluacion completa con sweep")
print("- Metricas: precision, recall, F1 por pregunta")
print("- Robustez Jaccard entre preguntas del mismo tema")

print("\n" + "="*70)
print("[OK] INTEGRACION COMPLETADA EXITOSAMENTE")
print("="*70)
print("\nPara evaluar retrieval real:")
print("  from app.models.rag.evaluation import evaluate_retrieval")
print("  resultado = evaluate_retrieval(k=10, sweep=True)")
print("  print(resultado['promedio'])")
print()
