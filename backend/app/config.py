# backend/app/config.py
import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSIST_DIR = os.getenv("PERSIST_DIR", os.path.join(BASE_DIR, "..", "..", "chroma_db"))

# Get absolute path
#BASE_DIR = os.path.abspath(os.path.dirname(__file__))
#MODEL_PATH = os.path.join(BASE_DIR, "../multi_models/paraphrase-multilingual-MiniLM-L12-v2")
#EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/distiluse-base-multilingual-cased-v2")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET", "dev-secret")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
ACCESS_TOKEN_EXPIRE_DELTA = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

DATABASE_URL = os.getenv("DATABASE_URL")

# Accept both spellings
SUPER_ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL") 
SUPER_ADMIN_PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD") 

os.makedirs(PERSIST_DIR, exist_ok=True)
