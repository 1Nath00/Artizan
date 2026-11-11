"""
Mejoras en la generación de respuestas RAG.

Incluye:
- Prompts optimizados
- Estrategias de citas
- Verificación de alucinaciones
"""

from __future__ import annotations

import re
from typing import Any


# Prompt mejorado para generación rigurosa
IMPROVED_SYSTEM_PROMPT = """# ROL
Eres un profesor experto en historia del arte que responde con rigor académico absoluto.
Tu única fuente de verdad es el CONTEXTO proporcionado.

# RESTRICCIONES CRÍTICAS
1. ÚNICAMENTE uses información explícita en los FRAGMENTOS del CONTEXTO.
2. CITA TODOS los fragmentos que respalden cada afirmación, así: [1], [2], etc.
3. Si la pregunta NO puede responderse completamente con el CONTEXTO:
   - Responde qué SÍ sabes del contexto.
   - Menciona explícitamente qué información falta.
   - NUNCA inventes, supongas ni extraples.
4. NO repitas información ya mencionada.
5. NO inventes: fechas, nombres de artistas, obras, lugares, períodos.
6. Si no hay información suficiente en el contexto, responde:
   "No encuentro información suficiente en los documentos para responder completamente."
7. Responde SIEMPRE en español, académico y claro.

# ESTRATEGIA DE RESPUESTA
1. Identifica qué fragmentos son directamente relevantes para la pregunta.
2. Descarta los irrelevantes.
3. Ordena la información de manera lógica (cronológica, por importancia, etc.).
4. Redacta usando SOLO lo del contexto, citando TODAS las fuentes.
5. Verifica que cada afirmación tenga una cita.

# FORMATO DE SALIDA
- Respuesta en 3-8 oraciones completas y bien estructuradas.
- Cita al final de cada idea: [número].
- Usa conectores lógicos para claridad.
- Evita listas, usa párrafos.

# EJEMPLO
Pregunta: ¿Qué es el fauvismo y cuándo surgió?
Contexto: [1] El fauvismo fue un movimiento artístico de principios del siglo XX [2] que enfatizaba el color puro [3]. 
Surgió en París entre 1905 y 1910 [4].
Respuesta: El fauvismo fue un movimiento artístico de principios del siglo XX [1][3] que surgió en París 
entre 1905 y 1910 [4]. El movimiento enfatizaba el color puro [2]."""


def improved_build_messages(question: str, hits: list[dict[str, Any]]) -> list[dict[str, str]]:
    """
    Construye mensajes optimizados para el LLM.
    
    Cambios:
    1. Usa el prompt mejorado
    2. Etiqueta claramente cada fragmento con su número
    3. Agrupa fragmentos por documento para mejor contexto
    4. Limita el contexto a fragmentos más relevantes
    """
    
    # Agrupar fragmentos por documento
    by_document: dict[str, list[tuple[int, str]]] = {}
    for i, hit in enumerate(hits, 1):
        filename = hit.get("filename", "desconocido")
        text = hit.get("text", "")
        if filename not in by_document:
            by_document[filename] = []
        by_document[filename].append((i, text))
    
    # Construir contexto agrupado
    context_parts = []
    for filename, fragments in by_document.items():
        doc_header = f"**Documento: {filename}**"
        context_parts.append(doc_header)
        
        for fragment_num, text in fragments:
            context_parts.append(f"[{fragment_num}] {text}")
    
    context = "\n\n".join(context_parts)
    
    user_message = f"""# CONTEXTO
{context}

# PREGUNTA
{question}

# INSTRUCCIONES
- Responde SOLO con información del CONTEXTO anterior.
- Cita TODOS los fragmentos [n] que respalden cada afirmación.
- Si no hay suficiente información, dilo explícitamente.
- No inventes información."""
    
    return [
        {"role": "system", "content": IMPROVED_SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]


def extract_citations(text: str) -> list[int]:
    """
    Extrae los números de citas [1], [2], etc. de una respuesta.
    
    Returns:
        Lista de números de citas encontrados (en orden de aparición)
    """
    citations = []
    for match in re.finditer(r"\[(\d+)\]", text):
        citations.append(int(match.group(1)))
    return citations


def validate_citations(answer: str, num_fragments: int) -> dict[str, Any]:
    """
    Valida las citas en una respuesta.
    
    Retorna:
        - total_citations: Número de citas (incluyendo repetidas)
        - unique_citations: Número de fragmentos únicos citados
        - valid_citations: Citas que están dentro del rango correcto
        - invalid_citations: Citas fuera del rango [1, num_fragments]
        - missing_fragments: Fragmentos disponibles no citados
        - coverage: Porcentaje de fragmentos utilizados
    """
    citations = extract_citations(answer)
    valid_citations = [c for c in citations if 1 <= c <= num_fragments]
    invalid_citations = [c for c in citations if c < 1 or c > num_fragments]
    
    unique_valid = set(valid_citations)
    missing = set(range(1, num_fragments + 1)) - unique_valid
    
    coverage = 100.0 * len(unique_valid) / num_fragments if num_fragments > 0 else 0.0
    
    return {
        "total_citations": len(citations),
        "unique_citations": len(unique_valid),
        "valid_citations": len(valid_citations),
        "invalid_citations": len(invalid_citations),
        "invalid_ids": invalid_citations,
        "missing_fragments": sorted(list(missing)),
        "coverage": coverage,
    }


def detect_hallucinations(answer: str, context: str) -> dict[str, Any]:
    """
    Detecta posibles alucinaciones (afirmaciones no respaldadas por contexto).
    
    Estrategia:
    1. Busca nombres, fechas, números específicos
    2. Verifica que aparezcan en el contexto
    3. Retorna evidencia de lo encontrado y no encontrado
    """
    
    # Extraer potenciales entidades nombradas (años, nombres, etc.)
    # Esto es heurístico; un modelo real usaría NER
    
    suspicious_patterns = {
        "years": re.findall(r"\b(1[0-9]{3}|2[0-9]{3})\b", answer),
        "proper_nouns": re.findall(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b", answer),  # Nombres
    }
    
    grounded = {}
    for category, entities in suspicious_patterns.items():
        grounded[category] = {
            entity: entity in context
            for entity in entities
        }
    
    ungrounded = [
        entity
        for entities in grounded.values()
        for entity, found in entities.items()
        if not found
    ]
    
    return {
        "potential_hallucinations": len(ungrounded),
        "ungrounded_entities": ungrounded,
        "grounded_ratio": 1.0 - (len(ungrounded) / (len(ungrounded) + len(suspicious_patterns))),
    }


def count_response_stats(answer: str) -> dict[str, int]:
    """
    Calcula estadísticas de la respuesta.
    """
    words = answer.split()
    sentences = re.split(r"[.!?]+", answer)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "avg_sentence_length": len(words) // len(sentences) if sentences else 0,
        "paragraph_count": len(answer.split("\n\n")),
    }
