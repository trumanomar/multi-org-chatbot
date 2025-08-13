import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSIST_DIR = os.getenv("PERSIST_DIR", os.path.join(BASE_DIR, "..", "..", "chroma_data"))

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

os.makedirs(PERSIST_DIR, exist_ok=True)
