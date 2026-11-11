from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.middleware import logger
from app.models.rag import service

router = APIRouter(prefix="/models/rag", tags=["RAG - Art Knowledge"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500, description="Question about art history")
    top_k: int | None = Field(None, ge=1, le=20, description="Number of fragments to retrieve")


class Source(BaseModel):
    filename: str
    chunk: int
    distance: float
    text: str


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[Source]
    latency: float


class IndexResponse(BaseModel):
    documents: int
    chunks: int


class ReindexResponse(IndexResponse):
    duplicated_skipped: int
    files_skipped: int


class StatusResponse(BaseModel):
    indexed_chunks: int
    ready: bool


def _handle(exc: Exception, message: str) -> HTTPException:
    if isinstance(exc, service.RAGError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    logger.exception(message)
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)


@router.post("/ask", response_model=AskResponse)
async def ask(body: AskRequest, current_user: User = Depends(get_current_active_user)):
    """Answer a question using only the indexed documents, citing sources."""
    try:
        return await run_in_threadpool(service.ask, body.question, body.top_k)
    except Exception as exc:
        raise _handle(exc, "Could not answer the question.") from exc


@router.post("/evaluate/answer")
async def evaluate_one(body: AskRequest, current_user: User = Depends(get_current_active_user)):
    """Ask a question and score the answer without ground truth (format, grounding, LLM judge)."""
    from app.models.rag import evaluation

    def run():
        res = service.ask(body.question, body.top_k)
        return {**res, "metrics": evaluation.evaluate_answer(body.question, res["answer"], res["sources"])}

    try:
        return await run_in_threadpool(run)
    except Exception as exc:
        raise _handle(exc, "Could not evaluate the answer.") from exc


@router.get("/evaluate/retrieval")
async def evaluate_retrieval(k: int | None = None, current_user: User = Depends(get_current_active_user)):
    """Precision/recall/F1@k, k sweep and paraphrase robustness of the retriever."""
    from app.models.rag import evaluation

    try:
        return await run_in_threadpool(evaluation.evaluate_retrieval, k)
    except Exception as exc:
        raise _handle(exc, "Could not evaluate retrieval.") from exc


@router.get("/evaluate/gold")
async def evaluate_gold(judge: bool = True, current_user: User = Depends(get_current_active_user)):
    """Run the gold question set: ROUGE, BLEU, semantic similarity, keywords, judge, abstention."""
    from app.models.rag import evaluation

    try:
        return await run_in_threadpool(evaluation.evaluate_gold, judge)
    except Exception as exc:
        raise _handle(exc, "Could not run the evaluation.") from exc


@router.get("/status", response_model=StatusResponse)
async def rag_status(current_user: User = Depends(get_current_active_user)):
    """Report whether the vector index has content."""
    return await run_in_threadpool(service.index_status)


@router.post("/index", response_model=ReindexResponse)
async def reindex(current_user: User = Depends(get_current_active_user)):
    """Rebuild the index from every .txt/.json/.jsonl file in the RAG data directory."""
    try:
        return await run_in_threadpool(service.rebuild_index)
    except Exception as exc:
        raise _handle(exc, "Could not build the index.") from exc


@router.post("/documents", response_model=IndexResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description=".txt, .json or .jsonl file"),
    current_user: User = Depends(get_current_active_user),
):
    """Add (or replace) one document in the index."""
    filename = (file.filename or "").replace("\\", "/").split("/")[-1]
    if not filename.lower().endswith(service.EXTS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(service.EXTS)}",
        )
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 5 MB).")
    try:
        return await run_in_threadpool(service.add_document, filename, raw)
    except service.RAGError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise _handle(exc, "Could not index the document.") from exc
