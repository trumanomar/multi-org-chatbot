<<<<<<< HEAD
from typing import List

from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings

=======
# backend/app/VectorDB/DB.py

from __future__ import annotations

import os
from typing import List, Optional

# New, non-deprecated imports
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
# (Loaders are here if you need them in this module later)
# from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader

>>>>>>> 6d9ceb8768babb98fab896b71721555f845faf00
from app.config import PERSIST_DIR, EMBEDDING_MODEL

# Ensure persist directory exists
os.makedirs(PERSIST_DIR, exist_ok=True)

# Create the embedding function (HuggingFace small, fast model by default)
embedding_function = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

# Initialize / load the vector store (auto-loads existing index from PERSIST_DIR)
vectorstore = Chroma(
    persist_directory=PERSIST_DIR,
    embedding_function=embedding_function,
)
<<<<<<< HEAD
vectorstore = Chroma(persist_directory=PERSIST_DIR, embedding_function=embedding_function)


=======

def add_documents(docs) -> None:
    """
    Add a list of LangChain Documents (with .page_content and .metadata).
    """
    if not docs:
        return
    vectorstore.add_documents(docs)

def persist() -> None:
    # Some versions of langchain_chroma/Chroma won’t expose .persist()
    if hasattr(vectorstore, "persist"):
        vectorstore.persist()

def search_similar(query: str, k: int = 5):
    """
    Return top-k similar Documents (no scores).
    Each Document has .page_content and .metadata.
    """
    return vectorstore.similarity_search(query, k=k)

def search_with_scores(query: str, k: int = 5):
    """
    Return list of (Document, score) tuples.
    Lower scores mean closer matches.
    """
    return vectorstore.similarity_search_with_score(query, k=k)

def reset_index() -> None:
    """
    Optional helper: wipe the current index on disk and reinitialize.
    Use with caution.
    """
    # Close existing reference
    global vectorstore
    del vectorstore

    # Remove persisted files
    # (For Chroma, directory deletion is enough)
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

    # Re-create store
    os.makedirs(PERSIST_DIR, exist_ok=True)
    new_store = Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embedding_function,
    )
    vectorstore = new_store
>>>>>>> 6d9ceb8768babb98fab896b71721555f845faf00
