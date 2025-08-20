# backend/app/config.py
import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSIST_DIR = os.getenv("PERSIST_DIR", os.path.join(BASE_DIR, "..", "..", "chroma_data"))

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET", "dev-secret")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
ACCESS_TOKEN_EXPIRE_DELTA = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root@HOST:3306/chatbot_rag")

# Accept both spellings
SUPER_ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL") or os.getenv("SUPERADMIN_EMAIL", "sadmin@gmail.com")
SUPER_ADMIN_PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD") or os.getenv("SUPERADMIN_PASSWORD", "123456")

os.makedirs(PERSIST_DIR, exist_ok=True)
