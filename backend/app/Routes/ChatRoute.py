from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Any, Dict, List
import os
from sqlalchemy.orm import Session

# Database imports
from app.DB.db import get_db
from app.Models.tables import ChatSession, ChatMessage, User
from app.auth.dependencies import get_current_principal, get_current_user_db

# Vector search helpers (module-level)
from app.VectorDB import DB as vectordb
from app.utilis.greetings import (
    is_greeting,
    detect_language,
    make_greeting_response,
    localized_not_found,
)

# OpenAI-compatible SDK (works with OpenAI, Ollama, LM Studio, Groq via base_url)
from openai import OpenAI

router = APIRouter(tags=["Chat"])

# ---------- Schemas ----------
class ChatQuery(BaseModel):
    message: str = Field(..., description="User question")
    k: int = Field(5, ge=1, le=50, description="Top-K retrieved chunks")

class ChatAnswer(BaseModel):
    answer: str
    sources: List[Dict[str, str]]
    session_id: int
    message_id: int

# ---------- Prompt ----------
SYSTEM_INSTRUCTIONS = (
    "You are a helpful assistant for an internal knowledge base.\n"
    "ONLY answer using the provided context below. Do not use outside knowledge.\n"
    "Do not include the raw [Source ...] tags or file paths in your answer; sources will be attached separately.\n"
    "If the answer is not present in the context, reply exactly:\n"
    "\"I couldn’t find this in the knowledge base.\"\n"
    "Be concise and factual."
)

# ---------- Helpers ----------
def _is_document(x: Any) -> bool:
    return hasattr(x, "page_content") and hasattr(x, "metadata")

def _normalize_hit(hit: Any) -> Dict[str, Any]:
    # Accept: Document | dict | (doc, score) | (dict, score) | str
    score = None
    obj = hit
    if isinstance(hit, tuple) and len(hit) == 2:
        obj, score = hit

    if _is_document(obj):
        return {"page_content": obj.page_content or "", "metadata": obj.metadata or {}, "score": score}
    if isinstance(obj, dict):
        return {
            "page_content": obj.get("page_content") or obj.get("content") or "",
            "metadata": obj.get("metadata") or {},
            "score": score,
        }
    if isinstance(obj, str):
        return {"page_content": obj, "metadata": {}, "score": score}
    return {"page_content": "", "metadata": {}, "score": score}

def _build_context(hits: List[Dict[str, Any]], max_chars: int = 12000) -> str:
    blocks, total = [], 0
    for i, h in enumerate(hits, 1):
        meta = h.get("metadata") or {}
        src = meta.get("source") or meta.get("file_path") or meta.get("filename") or "unknown"
        txt = (h.get("page_content") or "").strip()
        if not txt:
            continue
        chunk = txt if len(txt) <= 2000 else (txt[:2000] + "…")
        block = f"[Source {i}: {src}]\n{chunk}"
        if total + len(block) > max_chars:
            break
        blocks.append(block)
        total += len(block)
    return "\n\n---\n\n".join(blocks)

def _extract_sources(hits: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    out, seen = [], set()
    for h in hits:
        meta = h.get("metadata") or {}
        src = meta.get("source") or meta.get("file_path") or meta.get("filename") or ""
        if not src or src.lower() == "unknown":
            continue
        txt = (h.get("page_content") or "").strip()
        snippet = (txt[:300] + "…") if len(txt) > 300 else txt
        # De-dupe by source only (simple & effective)
        if src in seen:
            continue
        seen.add(src)
        out.append({"source_file": src, "snippet": snippet})
    return out

# ---------- LLM ----------
def _answer_with_stub(context: str, question: str) -> str:
    if not context.strip():
        return "I couldn’t find this in the knowledge base."
    return f"Based on the provided documents: {question}"

def _answer_with_openai(context: str, question: str) -> str:
    """
    OpenAI-compatible Chat Completions call.
    Uses OPENAI_BASE_URL (e.g., http://localhost:11434/v1 for Ollama),
    OPENAI_API_KEY, and LLM_MODEL.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("LLM_MODEL", "llama3.1:8b-instruct-q4_K_M")

    if not api_key:
        return _answer_with_stub(context, question)

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer strictly from the context."},
        ]
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
            max_tokens=500,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text or "I couldn’t find this in the knowledge base."
    except Exception as e:
        # Keep it simple and robust
        print(f"[chat] LLM call failed; falling back. Error: {e}")
        return _answer_with_stub(context, question)

# ---------- Routes ----------
@router.get("/chat/debug_env")
def debug_env():
    return {
        "has_openai_api_key": bool(os.getenv("OPENAI_API_KEY")),
        "llm_model": os.getenv("LLM_MODEL"),
        "openai_base_url": os.getenv("OPENAI_BASE_URL"),
    }

@router.post("/chat/query", response_model=ChatAnswer)
def chat_query(
    payload: ChatQuery, 
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db),
    db: Session = Depends(get_db)
):
    q = payload.message.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty message")

    # Detect greeting; if yes, respond in same language but still save to history
    greeting_lang = is_greeting(q)
    if greeting_lang:
        answer = make_greeting_response(greeting_lang)
        # Save chat session and message even for greetings
        session = ChatSession(user_id=user.id, domain_id=principal.domain_id)
        db.add(session)
        db.commit()
        db.refresh(session)

        message = ChatMessage(
            session_id=session.id,
            user_id=user.id,
            question=q,
            answer=answer,
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        return ChatAnswer(answer=answer, sources=[], session_id=session.id, message_id=message.id)

    # Detect user language for possible localized fallbacks
    user_lang = detect_language(q)

    raw = vectordb.search_similar(q, payload.k)
    hits = [_normalize_hit(h) for h in (raw or []) if h is not None]

    if not hits or not any((h.get("page_content") or "").strip() for h in hits):
        answer = localized_not_found(user_lang)
        # Save chat session and message even when no hits found
        session = ChatSession(user_id=user.id, domain_id=principal.domain_id)
        db.add(session)
        db.commit()
        db.refresh(session)

        message = ChatMessage(
            session_id=session.id,
            user_id=user.id,
            question=q,
            answer=answer,
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        return ChatAnswer(answer=answer, sources=[], session_id=session.id, message_id=message.id)

    context = _build_context(hits)
    answer = _answer_with_openai(context, q) or "I couldn’t find this in the knowledge base."

    # If the model/stub returned the fallback phrase, localize it
    if (answer or "").strip() == "I couldn’t find this in the knowledge base.":
        answer = localized_not_found(user_lang)

    # Save chat session and message
    session = ChatSession(user_id=user.id, domain_id=principal.domain_id)
    db.add(session)
    db.commit()
    db.refresh(session)

    message = ChatMessage(
        session_id=session.id,
        user_id=user.id,
        question=q,
        answer=answer,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    return ChatAnswer(answer=answer, sources=_extract_sources(hits), session_id=session.id, message_id=message.id)

# ---------- Chat History Endpoints ----------
@router.get("/chat/sessions/{user_id}")
def get_user_chat_sessions(user_id: int, db: Session = Depends(get_db)):
    """Get all chat sessions for a user"""
    sessions = db.query(ChatSession).filter(ChatSession.user_id == user_id).order_by(ChatSession.created_at.desc()).all()
    return sessions

@router.get("/chat/messages/{session_id}")
def get_chat_messages(session_id: int, db: Session = Depends(get_db)):
    """Get all messages for a specific chat session"""
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
    return messages

@router.get("/chat/history/{user_id}")
def get_user_chat_history(user_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """Get recent chat history for a user with pagination"""
    # Get recent sessions
    sessions = db.query(ChatSession).filter(ChatSession.user_id == user_id).order_by(ChatSession.created_at.desc()).limit(limit).all()
    
    history = []
    for session in sessions:
        messages = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.asc()).all()
        history.append({
            "session_id": session.id,
            "created_at": session.created_at,
            "messages": [
                {
                    "id": msg.id,
                    "question": msg.question,
                    "answer": msg.answer,
                    "created_at": msg.created_at
                } for msg in messages
            ]
        })
    
    return history
