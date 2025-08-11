# backend/app/routes/BasicRoutes.py
from fastapi import APIRouter, Query
from app.VectorDB.DB import search_similar, search_with_scores

router = APIRouter(tags=["probe"])

@router.get("/probe")
def probe(
    query: str = Query(..., description="Your question / search text"),
    k: int = Query(5, ge=1, le=20, description="Top-k results"),
):
    """Return top-k similar chunks (no scores)."""
    docs = search_similar(query, k=k)
    return [{"text": d.page_content, "metadata": d.metadata} for d in docs]

@router.get("/probe_scores")
def probe_scores(
    query: str = Query(..., description="Your question / search text"),
    k: int = Query(5, ge=1, le=20, description="Top-k results"),
):
    """Return top-k similar chunks with similarity scores (lower = closer)."""
    pairs = search_with_scores(query, k=k)
    return [
        {"score": float(score), "text": doc.page_content, "metadata": doc.metadata}
        for doc, score in pairs
    ]
