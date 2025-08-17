from __future__ import annotations
import os
from typing import List

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from app.config import PERSIST_DIR, EMBEDDING_MODEL

# Embedding function
embedding_function = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

# Always load existing vectorstore if it exists
vectorstore = Chroma(
    persist_directory=PERSIST_DIR,
    embedding_function=embedding_function,
)


def add_documents(docs) -> None:
    """Append new documents to the existing vectorstore."""
    if not docs:
        return
    vectorstore.add_documents(docs)

def search_similar(query: str, k: int = 5, where: dict | None = None):
    """Return top-k similar Documents (optionally filtered by metadata)."""
    return vectorstore.similarity_search(query, k=k, filter=where)

def search_with_scores(query: str, k: int = 5, where: dict | None = None):
    """Return top-k similar Documents with similarity scores (optionally filtered)."""
    return vectorstore.similarity_search_with_score(query, k=k, filter=where)

def search_similar_for_domain(query: str, domain_id: int, k: int = 5):
    # Chroma supports metadata filtering
    return vectorstore.similarity_search(query, k=k, filter={"domain_id": domain_id})

def persist() -> None:
    """Save current index to disk."""
    if hasattr(vectorstore, "persist"):
        vectorstore.persist()

def search_similar(query: str, k: int = 5):
    """Return top-k similar Documents."""
    return vectorstore.similarity_search(query, k=k)

def search_with_scores(query: str, k: int = 5):
    """Return top-k similar Documents with similarity scores."""
    return vectorstore.similarity_search_with_score(query, k=k)

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
