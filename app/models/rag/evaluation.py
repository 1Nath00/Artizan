"""
RAG evaluation metrics (port of the reference notebook).

With ground truth: ROUGE-1/2/L, BLEU, semantic similarity, keyword match.
Without ground truth: format/citation heuristics, grounding, LLM-as-a-judge, abstention.
Retrieval: precision/recall/F1@k at document level and robustness across paraphrases.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from itertools import combinations
from typing import Any

from app import config
from app.models.rag import service

STOP = set("el la los las un una unos unas de del al y o en que es se por con para su sus lo a como mas muy".split())
ABSTAIN = "no encuentro informacion suficiente"
LEAK_PATTERNS = [r"\bseg[uú]n el contexto\b", r"\bfragmentos? \[?\d", r"\bcomo (modelo|ia|asistente)\b", r"\bas an ai\b"]

JUDGE_SYSTEM = """Eres un evaluador estricto de un sistema de preguntas y respuestas sobre historia del arte.
Recibirás una PREGUNTA, el CONTEXTO recuperado y la RESPUESTA del sistema. Califica de 1 a 5:
- fidelidad: la respuesta solo afirma cosas respaldadas por el CONTEXTO (1 = inventa cosas, 5 = totalmente respaldada).
- completitud: responde todo lo que se pregunta.
- relevancia: se centra en la pregunta, sin divagar.
- tono: académico, claro y profesional.
Marca alucinacion=true si la respuesta contiene datos que NO están en el CONTEXTO.
Si la respuesta dice que no hay información suficiente, evalúa si eso es razonable dado el CONTEXTO.
Responde SOLO con JSON: {"fidelidad":int,"completitud":int,"relevancia":int,"tono":int,"alucinacion":bool,"comentario":"una frase"}"""

TOPICS = {"cubismo": r"cubis", "barroco": r"barroc"}

QUESTIONS = {
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
REFS = {
    "cubismo": [
        "El cubismo es un movimiento artístico de vanguardia surgido en París a principios del siglo XX, iniciado por Pablo Picasso y Georges Braque, que descompone los objetos en formas geométricas y los representa desde varios puntos de vista a la vez, rompiendo con la perspectiva tradicional.",
        "El cubismo, desarrollado en París entre 1907 y 1914, abandona la imitación de la realidad y construye la imagen mediante planos y formas geométricas simultáneas, siguiendo la huella de Cézanne.",
    ],
    "barroco": [
        "El barroco es un estilo artístico y cultural que se desarrolló en Europa durante el siglo XVII y parte del XVIII, caracterizado por el dinamismo, el dramatismo, los fuertes contrastes de luz y sombra y la ornamentación abundante.",
        "El barroco es el arte del movimiento, la teatralidad y la exuberancia decorativa, vinculado a la Contrarreforma y a las monarquías absolutas, con un uso intenso del claroscuro.",
    ],
}
KEYWORDS = {
    "cubismo": ["picasso", "braque", "geometric", "paris"],
    "barroco": ["xvii", "movimiento", "luz|claroscuro", "ornament|decorac"],
}
OUT_OF_SCOPE = ["¿Cuál es la capital de Japón?", "¿Cómo se programa un bucle for en Python?"]


# ---------- Tokenization and overlap metrics ----------
def _norm(s: Any) -> str:
    s = unicodedata.normalize("NFD", str(s).lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def tok(s: Any) -> list[str]:
    return re.findall(r"[a-z0-9]+", re.sub(r"\[\d+\]", " ", _norm(s)))


def _prf(match: float, n_pred: int, n_ref: int) -> tuple[float, float, float]:
    p = match / n_pred if n_pred else 0.0
    r = match / n_ref if n_ref else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


def _ngrams(t: list[str], n: int) -> Counter:
    return Counter(tuple(t[i : i + n]) for i in range(len(t) - n + 1))


def rouge_n(pred: str, ref: str, n: int) -> tuple[float, float, float]:
    P, R = _ngrams(tok(pred), n), _ngrams(tok(ref), n)
    return _prf(sum((P & R).values()), sum(P.values()), sum(R.values()))


def _lcs_len(a: list[str], b: list[str]) -> int:
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b, 1):
            cur.append(prev[j - 1] + 1 if x == y else max(prev[j], cur[-1]))
        prev = cur
    return prev[-1]


def rouge_l(pred: str, ref: str) -> tuple[float, float, float]:
    a, b = tok(pred), tok(ref)
    return _prf(_lcs_len(a, b), len(a), len(b))


def bleu(pred: str, refs: str | list[str], max_n: int = 4) -> float:
    refs = [refs] if isinstance(refs, str) else refs
    p, rs = tok(pred), [tok(r) for r in refs]
    if not p or not any(rs):
        return 0.0
    n_max = min(max_n, len(p))
    log_sum = 0.0
    for n in range(1, n_max + 1):
        P = _ngrams(p, n)
        total = sum(P.values())
        max_ref: Counter = Counter()
        for r in rs:
            for g, c in _ngrams(r, n).items():
                max_ref[g] = max(max_ref[g], c)
        match = sum(min(c, max_ref[g]) for g, c in P.items())
        log_sum += math.log(match / total if match else 1 / (2 * total))
    ref_len = min((len(r) for r in rs), key=lambda L: (abs(L - len(p)), L))
    bp = 1.0 if len(p) > ref_len else math.exp(1 - ref_len / len(p))
    return bp * math.exp(log_sum / n_max)


def semantic_sim(pred: str, refs: str | list[str]) -> float:
    refs = [refs] if isinstance(refs, str) else refs
    e = service._embedder().encode([f"query: {pred}"] + [f"query: {r}" for r in refs], normalize_embeddings=True)
    return float(max(e[1:] @ e[0]))


def keyword_match(pred: str, keywords: list[str]) -> float | None:
    """Each keyword may list alternatives with '|' (e.g. 'luz|claroscuro')."""
    if not keywords:
        return None
    text = _norm(pred)
    hit = sum(any(_norm(alt) in text for alt in kw.split("|")) for kw in keywords)
    return hit / len(keywords)


def is_abstention(answer: str) -> bool:
    return ABSTAIN in _norm(answer)


# ---------- Reference-free metrics ----------
def heuristics(answer: str, hits: list[dict[str, Any]]) -> dict[str, Any]:
    abst = is_abstention(answer)
    sents = [s for s in re.split(r"(?<=[.!?])\s+", answer.strip()) if s]
    cites = {int(x) for x in re.findall(r"\[(\d+)\]", answer)}
    ctx = set(tok(" ".join(h["text"] for h in hits)))
    a_tok = [t for t in tok(answer) if t not in STOP]
    grounded = sum(t in ctx for t in a_tok) / len(a_tok) if a_tok else 0.0
    return {
        "abstuvo": abst,
        "n_palabras": len(answer.split()),
        "n_oraciones": len(sents),
        "formato_3a6_oraciones": abst or 3 <= len(sents) <= 6,
        "tiene_citas": bool(cites),
        "citas_validas": bool(cites) and all(1 <= c <= len(hits) for c in cites),
        "fundamentacion": round(grounded, 3),
        "fuga_de_prompt": any(re.search(p, answer.lower()) for p in LEAK_PATTERNS),
    }


def llm_judge(question: str, answer: str, hits: list[dict[str, Any]], ref: str | None = None) -> dict[str, Any]:
    ctx = "\n\n".join(f"[{i + 1}] {h['text'][:700]}" for i, h in enumerate(hits))
    user = f"PREGUNTA: {question}\n\nCONTEXTO:\n{ctx}\n\nRESPUESTA DEL SISTEMA:\n{answer}"
    if ref:
        user += f"\n\nREFERENCIA (opcional, solo orientativa):\n{ref}"
    try:
        import ollama

        r = ollama.Client(host=config.OLLAMA_HOST).chat(
            model=config.RAG_JUDGE_MODEL,
            format="json",
            messages=[{"role": "system", "content": JUDGE_SYSTEM}, {"role": "user", "content": user}],
            options={"temperature": 0, "num_ctx": config.RAG_NUM_CTX},
        )
        d = json.loads(r["message"]["content"])
        sc = {k: max(1, min(5, int(d.get(k, 0) or 0))) for k in ("fidelidad", "completitud", "relevancia", "tono")}
        return {
            **{f"juez_{k}": v for k, v in sc.items()},
            "juez_promedio": round(sum(sc.values()) / 4, 2),
            "juez_alucinacion": bool(d.get("alucinacion", False)),
            "juez_comentario": str(d.get("comentario", ""))[:200],
        }
    except Exception as e:
        return {"juez_error": str(e)[:120]}


def evaluate_answer(
    question: str,
    answer: str,
    hits: list[dict[str, Any]],
    refs: str | list[str] | None = None,
    keywords: list[str] | None = None,
    judge: bool = True,
) -> dict[str, Any]:
    out = heuristics(answer, hits)
    if refs:
        refs = [refs] if isinstance(refs, str) else refs

        def best(fn):
            return max((fn(answer, r) for r in refs), key=lambda x: x[2])

        p1, r1, f1 = best(lambda a, b: rouge_n(a, b, 1))
        _, _, f2 = best(lambda a, b: rouge_n(a, b, 2))
        _, _, fl = best(rouge_l)
        out.update(
            {
                "rouge1_p": round(p1, 3),
                "rouge1_r": round(r1, 3),
                "rouge1_f1": round(f1, 3),
                "rouge2_f1": round(f2, 3),
                "rougeL_f1": round(fl, 3),
                "bleu": round(bleu(answer, refs), 3),
                "similitud_semantica": round(semantic_sim(answer, refs), 3),
            }
        )
    if keywords:
        out["palabras_clave"] = round(keyword_match(answer, keywords) or 0.0, 3)
    if judge:
        out.update(llm_judge(question, answer, hits, ref=refs[0] if refs else None))
    return out


# ---------- Retrieval evaluation ----------
def relevant_docs(min_mentions: int | None = None) -> dict[str, set[str]]:
    """Documents mentioning each topic at least `min_mentions` times."""
    min_mentions = min_mentions or config.RAG_MIN_MENTIONS
    docs = service.load_documents(config.RAG_DATA_DIR)
    return {
        t: {d["filename"] for d in docs if len(re.findall(pat, d["text"], flags=re.I)) >= min_mentions}
        for t, pat in TOPICS.items()
    }


def _prf_sets(retrieved: set[str], relevant: set[str]) -> tuple[float, float, float]:
    tp = len(retrieved & relevant)
    p = tp / len(retrieved) if retrieved else 0.0
    r = tp / len(relevant) if relevant else 0.0
    return p, r, (2 * p * r / (p + r) if (p + r) else 0.0)


def _mean(xs: list[float]) -> float:
    return round(sum(xs) / len(xs), 3) if xs else 0.0


def eval_retrieval(k: int, relevant: dict[str, set[str]]) -> list[dict[str, Any]]:
    rows = []
    for topic, qs in QUESTIONS.items():
        for q in qs:
            got = {h["filename"] for h in service.retrieve(q, k)}
            p, r, f1 = _prf_sets(got, relevant[topic])
            rows.append({"tema": topic, "pregunta": q, "precision": round(p, 3), "recall": round(r, 3), "f1": round(f1, 3)})
    return rows


def evaluate_retrieval(k: int | None = None, sweep: bool = True) -> dict[str, Any]:
    k = k or config.RAG_TOP_K
    relevant = relevant_docs()
    rows = eval_retrieval(k, relevant)
    result: dict[str, Any] = {
        "k": k,
        "relevantes": {t: sorted(s) for t, s in relevant.items()},
        "preguntas": rows,
        "promedio": {m: _mean([r[m] for r in rows]) for m in ("precision", "recall", "f1")},
    }
    if sweep:
        out = []
        for kk in (1, 3, 5, 8, 10):
            d = eval_retrieval(kk, relevant)
            out.append({"k": kk, **{m: _mean([r[m] for r in d]) for m in ("precision", "recall", "f1")}})
        result["barrido_k"] = out
    rob = {}
    for t, qs in QUESTIONS.items():
        sets = [{h["filename"] for h in service.retrieve(q, k)} for q in qs]
        pairs = list(combinations(sets, 2))
        rob[t] = round(sum(len(a & b) / len(a | b) for a, b in pairs) / len(pairs), 3)
    result["robustez_jaccard"] = rob
    return result


# ---------- Full gold evaluation ----------
def evaluate_gold(judge: bool = True, k: int | None = None) -> dict[str, Any]:
    rows = []
    for topic, qs in QUESTIONS.items():
        for q in qs:
            res = service.ask(q, k)
            ev = evaluate_answer(q, res["answer"], res["sources"], refs=REFS[topic], keywords=KEYWORDS[topic], judge=judge)
            rows.append({"tema": topic, "pregunta": q, "latencia_s": res["latency"], **ev, "respuesta": res["answer"]})

    abst = []
    for q in OUT_OF_SCOPE:
        res = service.ask(q)
        abst.append({"pregunta": q, "se_abstuvo": is_abstention(res["answer"]), "respuesta": res["answer"][:160]})

    def avg(key: str) -> float | None:
        vals = [float(r[key]) for r in rows if key in r]
        return _mean(vals) if vals else None

    summary = {
        "rouge1_f1": avg("rouge1_f1"),
        "rouge2_f1": avg("rouge2_f1"),
        "rougeL_f1": avg("rougeL_f1"),
        "bleu": avg("bleu"),
        "similitud_semantica": avg("similitud_semantica"),
        "palabras_clave": avg("palabras_clave"),
        "fundamentacion": avg("fundamentacion"),
        "juez_promedio": avg("juez_promedio"),
        "tasa_alucinacion_juez": avg("juez_alucinacion"),
        "formato_ok": avg("formato_3a6_oraciones"),
        "citas_validas": avg("citas_validas"),
        "abstencion_correcta": _mean([float(a["se_abstuvo"]) for a in abst]),
        "latencia_media_s": avg("latencia_s"),
    }
    return {"resumen": summary, "respuestas": rows, "abstencion": abst}
