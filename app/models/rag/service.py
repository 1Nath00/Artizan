"""
RAG over art-history documents (.txt / .json / .jsonl).

Pipeline: read files -> chunk -> embed (sentence-transformers) -> ChromaDB ->
retrieve top-k -> answer with an Ollama LLM. Heavy dependencies are loaded lazily.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import threading
import time
import unicodedata
from collections import Counter
from functools import lru_cache
from typing import Any

from app import config

EXTS = (".txt", ".json", ".jsonl")
COLLECTION_NAME = "arte"
logger = logging.getLogger(__name__)

TEXT_KEYS = [
    "titulo", "title", "texto", "text", "contenido", "content", "cuerpo", "body",
    "descripcion", "description", "resumen", "summary",
]

SYSTEM_PROMPT = """# ROL
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
6. Si no hay información suficiente, responde:
   "No encuentro información suficiente en los documentos."
7. Responde SIEMPRE en español, académico y claro.

# ESTRATEGIA
1. Identifica qué fragmentos son directamente relevantes.
2. Ordena la información de manera lógica.
3. Redacta usando SOLO lo del contexto, citando TODAS las fuentes.

# FORMATO
Respuesta en párrafos (3-8 oraciones), cita al final de cada idea: [número]."""

_index_lock = threading.Lock()
_LEXICAL_STOP_WORDS = frozenset(
    "a al algo como con cual cuales cuando de del desde donde el en es esta fue ha "
    "la las lo los mas o para por que se su sus un una y".split()
)


class RAGError(Exception):
    """Raised for expected RAG failures (no index, LLM unavailable, ...)."""


# ---------- Document reading ----------
def _clean(text: str) -> str:
    text = text.replace("\xad", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def _decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return ""


def _json_to_text(obj: Any) -> str:
    if isinstance(obj, str):
        return obj
    if isinstance(obj, (list, tuple)):
        return "\n".join(t for t in (_json_to_text(x) for x in obj) if t.strip())
    if isinstance(obj, dict):
        preferred = [k for k in obj if str(k).lower() in TEXT_KEYS]
        values = [obj[k] for k in preferred] if preferred else list(obj.values())
        return "\n".join(t for t in (_json_to_text(v) for v in values) if t.strip())
    return ""


def parse_document(filename: str, raw: bytes) -> str:
    text = _decode(raw)
    low = filename.lower()
    if low.endswith(".json"):
        try:
            extracted = _clean(_json_to_text(json.loads(text)))
            return _clean(re.sub(r"^[^\r\n]*?\.pdf\s+pdf(?:\s+|$)", "", extracted, flags=re.IGNORECASE))
        except json.JSONDecodeError:
            return _clean(text)
    if low.endswith(".jsonl"):
        items = []
        for line in text.splitlines():
            if line.strip():
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    items.append(line)
        return _clean(_json_to_text(items))
    return _clean(text)


def _load_documents(data_dir: str) -> tuple[list[dict[str, str]], int]:
    documents = []
    skipped = 0
    for root, _, names in os.walk(data_dir):
        txt_stems = {
            os.path.splitext(name)[0].casefold()
            for name in names if name.lower().endswith(".txt")
        }
        for fn in sorted(names):
            if not fn.lower().endswith(EXTS):
                continue
            if fn.lower().endswith(".json") and os.path.splitext(fn)[0].casefold() in txt_stems:
                skipped += 1
                logger.warning("Skipping duplicate JSON document: %s", os.path.relpath(os.path.join(root, fn), data_dir))
                continue
            path = os.path.join(root, fn)
            with open(path, "rb") as f:
                text = parse_document(fn, f.read())
            if text:
                documents.append({"filename": os.path.relpath(path, data_dir), "text": text})
    return documents, skipped


def load_documents(data_dir: str) -> list[dict[str, str]]:
    return _load_documents(data_dir)[0]


# ---------- Chunking ----------
def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    buf = ""
    for p in text.split("\n"):
        p = p.strip()
        if not p:
            continue
        while len(p) > size:
            cut = p.rfind(" ", 0, size)
            cut = cut if cut > size * 0.5 else size
            if buf:
                chunks.append(buf)
                buf = ""
            chunks.append(p[:cut])
            p = p[cut:].strip()
        if len(buf) + len(p) + 1 > size and buf:
            chunks.append(buf)
            buf = buf[-overlap:] + " " + p
        else:
            buf = (buf + " " + p).strip()
    if buf:
        chunks.append(buf)
    return [c.strip() for c in chunks if len(c.strip()) > 80]


# ---------- Embeddings / vector store ----------
@lru_cache(maxsize=1)
def _embedder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(config.RAG_EMBEDDING_MODEL)


def _embed_passages(texts: list[str]) -> list[list[float]]:
    return _embedder().encode(
        [f"passage: {t}" for t in texts], batch_size=64, normalize_embeddings=True
    ).tolist()


def _embed_query(q: str) -> list[list[float]]:
    return _embedder().encode([f"query: {q}"], normalize_embeddings=True).tolist()


def _client():
    import chromadb

    return chromadb.PersistentClient(path=config.RAG_DB_DIR)


def _get_collection():
    try:
        return _client().get_collection(COLLECTION_NAME)
    except Exception as exc:
        raise RAGError("The RAG index is empty. Upload documents or call POST /models/rag/index first.") from exc


def _add_records(collection, records: list[dict[str, Any]]) -> None:
    batch = 500
    for i in range(0, len(records), batch):
        b = records[i : i + batch]
        collection.upsert(
            ids=[r["id"] for r in b],
            documents=[r["text"] for r in b],
            embeddings=_embed_passages([r["text"] for r in b]),
            metadatas=[{"filename": r["filename"], "chunk": r["chunk"]} for r in b],
        )


def _normalize_chunk(text: str) -> str:
    return " ".join(
        "".join(" " if unicodedata.category(char).startswith(("P", "S")) else char
                for char in text.casefold()).split()
    )


def _records_with_stats(documents: list[dict[str, str]]) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    skipped = 0
    for document in documents:
        for i, chunk in enumerate(chunk_text(document["text"], config.RAG_CHUNK_SIZE, config.RAG_CHUNK_OVERLAP)):
            normalized = _normalize_chunk(chunk)
            if normalized in seen:
                skipped += 1
                continue
            seen.add(normalized)
            records.append({"id": f"{document['filename']}::{i}", "filename": document["filename"],
                            "chunk": i, "text": chunk})
    return records, skipped


def _to_records(documents: list[dict[str, str]]) -> list[dict[str, Any]]:
    return _records_with_stats(documents)[0]


def rebuild_index() -> dict[str, int]:
    """Rebuild the whole index from RAG_DATA_DIR."""
    if not os.path.isdir(config.RAG_DATA_DIR):
        raise RAGError(f"Data directory '{config.RAG_DATA_DIR}' does not exist.")
    documents, files_skipped = _load_documents(config.RAG_DATA_DIR)
    if not documents:
        raise RAGError(f"No usable documents ({', '.join(EXTS)}) found in '{config.RAG_DATA_DIR}'.")
    records, duplicated_skipped = _records_with_stats(documents)
    if not records:
        raise RAGError("No indexable chunks were produced from the documents.")
    with _index_lock:
        # Don't rmtree the DB dir: on Windows chroma keeps the sqlite files locked, so the
        # old collection survived and create_collection failed with "already exists".
        client = _client()
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        collection = client.create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
        _add_records(collection, records)
    return {"documents": len(documents), "chunks": len(records),
            "duplicated_skipped": duplicated_skipped, "files_skipped": files_skipped}


def add_document(filename: str, raw: bytes) -> dict[str, int]:
    """Add (or replace) a single uploaded document in the index."""
    text = parse_document(filename, raw)
    records = _to_records([{"filename": filename, "text": text}]) if text else []
    if not records:
        raise RAGError("The document has no usable text.")
    with _index_lock:
        collection = _client().get_or_create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
        collection.delete(where={"filename": filename})
        _add_records(collection, records)
    return {"documents": 1, "chunks": len(records)}


def index_status() -> dict[str, Any]:
    try:
        count = _client().get_collection(COLLECTION_NAME).count()
    except Exception:
        count = 0
    return {"indexed_chunks": count, "ready": count > 0}


# ---------- Retrieval + generation ----------
def _lexical_ranks(question: str, texts: list[str]) -> list[int]:
    normalized = unicodedata.normalize("NFD", question.lower())
    query_terms = {
        token
        for token in re.findall(r"[a-z0-9]+", "".join(c for c in normalized if not unicodedata.combining(c)))
        if token not in _LEXICAL_STOP_WORDS
    }
    if not query_terms or not texts:
        return []

    documents = []
    for text in texts:
        normalized = unicodedata.normalize("NFD", text.lower())
        documents.append(
            [
                token
                for token in re.findall(
                    r"[a-z0-9]+", "".join(c for c in normalized if not unicodedata.combining(c))
                )
                if token not in _LEXICAL_STOP_WORDS
            ]
        )

    document_frequency = Counter(term for tokens in documents for term in set(tokens))
    average_length = sum(map(len, documents)) / len(documents) or 1
    scores: dict[int, float] = {}
    for index, tokens in enumerate(documents):
        frequencies = Counter(tokens)
        score = 0.0
        for term in query_terms:
            frequency = frequencies[term]
            if frequency:
                idf = math.log(1 + (len(documents) - document_frequency[term] + 0.5) /
                               (document_frequency[term] + 0.5))
                normalization = frequency + 1.2 * (0.25 + 0.75 * len(tokens) / average_length)
                score += idf * frequency * 2.2 / normalization
        if score:
            scores[index] = score
    return sorted(scores, key=lambda index: (-scores[index], index))


def retrieve(
    question: str, 
    k: int | None = None,
    use_deduplication: bool = True,
    dedup_threshold: float = 0.7
) -> list[dict[str, Any]]:
    """
    Retrieve top-k relevant chunks for a question.
    
    Args:
        question: User's question
        k: Number of chunks to return (defaults to config.RAG_TOP_K)
        use_deduplication: Whether to remove duplicate chunks
        dedup_threshold: Similarity threshold for deduplication (0-1)
    
    Returns:
        List of relevant chunks with metadata
    """
    k = k or config.RAG_TOP_K
    collection = _get_collection()
    candidate_count = min(collection.count(), max(k * 4, 20))
    if not candidate_count:
        raise RAGError("The RAG index is empty. Upload documents or call POST /models/rag/index first.")
    res = collection.query(query_embeddings=_embed_query(question), n_results=candidate_count)
    hits = [
        {"text": text, "filename": metadata["filename"], "chunk": metadata["chunk"], "distance": distance}
        for text, metadata, distance in zip(
            res["documents"][0], res["metadatas"][0], res["distances"][0]
        )
    ]

    # Reciprocal-rank fusion lets exact term matches help without discarding semantic matches.
    scores = {index: 1 / (60 + index + 1) for index in range(len(hits))}
    for rank, index in enumerate(_lexical_ranks(question, [hit["text"] for hit in hits]), 1):
        scores[index] += 1 / (60 + rank)
    
    ranked_hits = [hit for index, hit in sorted(enumerate(hits), key=lambda item: -scores[item[0]])[:k]]
    
    # Apply deduplication if requested
    if use_deduplication:
        from app.models.rag.retrieval_optimizations import deduplicate_hits
        ranked_hits = deduplicate_hits(ranked_hits, similarity_threshold=dedup_threshold)
    
    return ranked_hits[:k]


def build_messages(question: str, hits: list[dict[str, Any]]) -> list[dict[str, str]]:
    # Group fragments by document for better context
    by_document: dict[str, list[tuple[int, str]]] = {}
    for i, h in enumerate(hits, 1):
        filename = h.get("filename", "desconocido")
        if filename not in by_document:
            by_document[filename] = []
        by_document[filename].append((i, h.get("text", "")))
    
    # Build context with document grouping
    context_parts = []
    for filename, fragments in by_document.items():
        doc_header = f"## Documento: {filename}"
        context_parts.append(doc_header)
        
        for fragment_num, text in fragments:
            context_parts.append(f"[{fragment_num}] {text}")
    
    context = "\n\n".join(context_parts)
    
    user = f"""# CONTEXTO
{context}

# PREGUNTA
{question}

# INSTRUCCIONES
- Responde SOLO con información del CONTEXTO.
- Cita TODOS los fragmentos [n] que respalden cada afirmación.
- Si no hay suficiente información, dilo explícitamente.
- No inventes información."""
    
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def ask(question: str, k: int | None = None) -> dict[str, Any]:
    t0 = time.time()
    t_embed = time.time()
    hits = retrieve(question, k)
    t_retrieval = time.time() - t_embed
    
    try:
        import ollama

        t_llm = time.time()
        response = ollama.Client(host=config.OLLAMA_HOST).chat(
            model=config.RAG_LLM_MODEL,
            messages=build_messages(question, hits),
            options={"temperature": config.RAG_TEMPERATURE, "num_ctx": config.RAG_NUM_CTX},
        )
        t_llm = time.time() - t_llm
    except Exception as exc:
        raise RAGError(
            f"Could not reach Ollama at {config.OLLAMA_HOST} with model '{config.RAG_LLM_MODEL}'. "
            f"Make sure `ollama serve` is running and the model is pulled. Cause: {type(exc).__name__}: {exc}"
        ) from exc
    
    return {
        "question": question,
        "answer": response["message"]["content"].strip(),
        "sources": hits,
        "latency": round(time.time() - t0, 2),
        "latency_breakdown": {
            "retrieval_ms": round(t_retrieval * 1000, 0),
            "llm_ms": round(t_llm * 1000, 0),
        }
    }


def retrieve_multiple_k(question: str, k_values: list[int] = None) -> dict[str, Any]:
    """
    Test retrieval with multiple K values to find optimal configuration.
    
    Args:
        question: User's question
        k_values: List of K values to test (defaults to [1, 3, 5, 8, 10, 12, 15, 20])
    
    Returns:
        Dictionary with results for each K value
    """
    k_values = k_values or [1, 3, 5, 8, 10, 12, 15, 20]
    results = {}
    
    for k in k_values:
        hits = retrieve(question, k)
        results[k] = {
            "hits_count": len(hits),
            "unique_documents": len(set(h["filename"] for h in hits)),
            "avg_distance": sum(h.get("distance", 0) for h in hits) / len(hits) if hits else 0,
            "hits": hits,
        }
    
    return {
        "question": question,
        "results": results
    }


def analyze_retrieval(question: str, k: int = 10) -> dict[str, Any]:
    """
    Analyze retrieval quality and statistics.
    """
    from app.models.rag.retrieval_optimizations import analyze_chunks
    
    hits = retrieve(question, k)
    stats = analyze_chunks(hits)
    
    return {
        "question": question,
        "k": k,
        "hits_count": len(hits),
        **stats
    }
