import os

# Make sure the Chroma DB directory is inside a persistent folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSIST_DIR = os.getenv("PERSIST_DIR", os.path.join(BASE_DIR, "..", "..", "chroma_data"))

# Model for embeddings
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Ensure persistence directory exists at startup
os.makedirs(PERSIST_DIR, exist_ok=True)
