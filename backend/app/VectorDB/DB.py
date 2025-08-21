from __future__ import annotations

import os
from typing import Optional, Dict, Any, List

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from app.config import PERSIST_DIR, MODEL_PATH

# --- Embeddings & vectorstore -------------------------------------------------
embedding_function = HuggingFaceEmbeddings(model_name=MODEL_PATH)

# Always load existing vectorstore if it exists
vectorstore = Chroma(
    persist_directory=PERSIST_DIR,
    embedding_function=embedding_function,
)

# --- Write --------------------------------------------------------------------
def add_documents(docs) -> None:
    """Append new documents to the existing vectorstore."""
    if not docs:
        return
    vectorstore.add_documents(docs)

def persist() -> None:
    """Save current index to disk."""
    if hasattr(vectorstore, "persist"):
        vectorstore.persist()

# --- Read / Search ------------------------------------------------------------
def search_similar(
    query: str,
    k: int = 5,
    metadata_filter: Optional[Dict[str, Any]] = None,
):
    """Return top-k similar Documents (optionally filtered by metadata)."""
    kwargs: Dict[str, Any] = {}
    if metadata_filter:
        kwargs["filter"] = metadata_filter
    return vectorstore.similarity_search(query, k=k, **kwargs)

def search_with_scores(
    query: str,
    k: int = 5,
    metadata_filter: Optional[Dict[str, Any]] = None,
):
    """Return top-k similar Documents with scores (optionally filtered)."""
    kwargs: Dict[str, Any] = {}
    if metadata_filter:
        kwargs["filter"] = metadata_filter
    return vectorstore.similarity_search_with_score(query, k=k, **kwargs)

def search_similar_for_domain(query: str, domain_id: int, k: int = 5):
    """Convenience wrapper for domain-scoped search."""
    return search_similar(query, k=k, metadata_filter={"domain_id": int(domain_id)})

# --- Delete -------------------------------------------------------------------
def delete_vectors(
    ids: Optional[List[str]] = None,
    where: Optional[Dict[str, Any]] = None,
) -> None:
    """Generic delete by explicit ids or an arbitrary filter."""
    if ids:
        vectorstore.delete(ids=ids)
    elif where:
        vectorstore.delete(where=where)

def delete_vectors_for_doc(*, doc_id: int, domain_id: int) -> None:
    """
    Delete all vectors for a given (doc_id, domain_id) using Chroma's filter grammar.

    NOTE: Chroma expects ONE top-level operator in 'where', so we use $and.
    """
    where: Dict[str, Any] = {
        "$and": [
            {"doc_id": {"$eq": int(doc_id)}},
            {"domain_id": {"$eq": int(domain_id)}},
        ]
    }
    try:
        vectorstore.delete(where=where)
        persist()
        print(f"[chroma] delete where={where} -> OK")
    except Exception as e:
        print(f"[chroma] delete where={where} FAILED: {e}")
        raise RuntimeError(f"Vector delete failed: {e}")

# Optional debug helper (handy while testing)
def debug_count_vectors_for_doc(*, doc_id: int, domain_id: int) -> int:
    where: Dict[str, Any] = {
        "$and": [
            {"doc_id": {"$eq": int(doc_id)}},
            {"domain_id": {"$eq": int(domain_id)}},
        ]
    }
    try:
        # Prefer collection.count if exposed
        return vectorstore._collection.count(where=where)  # type: ignore[attr-defined]
    except Exception:
        try:
            data = vectorstore.get(where=where, limit=None)
            return len((data or {}).get("ids", []))
        except Exception:
            return -1

# --- Reset --------------------------------------------------------------------
def reset_index() -> None:
    """Wipe current index from disk — use with caution."""
    global vectorstore
    del vectorstore

    for root, dirs, files in os.walk(PERSIST_DIR, topdown=False):
        for name in files:
            try:
                os.remove(os.path.join(root, name))
            except FileNotFoundError:
                pass
        for name in dirs:
            try:
                os.rmdir(os.path.join(root, name))
            except OSError:
                pass

    os.makedirs(PERSIST_DIR, exist_ok=True)
    vectorstore = Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embedding_function,
    )
