# backend/app/DB/db.py
from __future__ import annotations
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load backend/.env when this module is imported
BACKEND_ROOT = Path(__file__).resolve().parents[2]  # -> backend/
load_dotenv(BACKEND_ROOT / ".env")

# Prefer env vars; fall back to a local default (works on Windows)
DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("SQLALCHEMY_DATABASE_URL")
    or "mysql+pymysql://root:12345678@localhost:3306/chatbot_rag"
)

# Create engine (pre_ping avoids stale connections)
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

# Session & Base
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
