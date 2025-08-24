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
    session_id: int = Field(None, description="Existing session ID to continue conversation")

class ChatAnswer(BaseModel):
    answer: str
    sources: List[Dict[str, str]]
    session_id: int
    message_id: int
    domain_scope: str = Field(description="Domain that was searched")
    is_new_session: bool = Field(description="Whether this created a new session")

# ---------- Prompt ----------
SYSTEM_INSTRUCTIONS = (
    "You are a helpful assistant for a domain-specific internal knowledge base.\n"
    "ONLY answer using the provided context below. Do not use outside knowledge.\n"
    "Do not include the raw [Source ...] tags or file paths in your answer; sources will be attached separately.\n"
    "If the answer is not present in the context, reply exactly:\n"
    "\"I couldn't find this in the knowledge base.\"\n"
    "Be concise and factual.\n"
    "Stay within your domain expertise and do not provide information outside your assigned domain."
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

def _get_domain_scope_name(domain_id: int, is_super_admin: bool = False) -> str:
    """Get human-readable domain scope name"""
    if is_super_admin and domain_id is None:
        return "Global (All Domains)"
    
    domain_names = {
        1: "HR Department",
        2: "IT Department",
        3: "Finance Department", 
        4: "Legal Department"
    }
    return domain_names.get(domain_id, f"Domain {domain_id}")

# ---------- LLM ----------
def _answer_with_stub(context: str, question: str) -> str:
    if not context.strip():
        return "I couldn't find this in the knowledge base."
    return f"Based on the provided documents: {question}"

def _answer_with_openai(context: str, question: str, domain_name: str = None) -> str:
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
        
        # Enhanced system instructions with domain context
        system_prompt = SYSTEM_INSTRUCTIONS
        if domain_name:
            system_prompt += f"\n\nNote: You are specifically answering for {domain_name}. Only provide information relevant to this domain."
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer strictly from the context."},
        ]
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
            max_tokens=500,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text or "I couldn't find this in the knowledge base."
    except Exception as e:
        # Keep it simple and robust
        print(f"[chat] LLM call failed; falling back. Error: {e}")
        return _answer_with_stub(context, question)

def _get_or_create_session(
    db: Session, 
    user: User, 
    domain_id: int,
    existing_session_id: int = None
) -> tuple[ChatSession, bool]:
    """Get existing session or create new one. Returns (session, is_new_session)"""
    try:
        # If session_id provided, try to get existing session
        if existing_session_id:
            session = db.query(ChatSession).filter(
                ChatSession.id == existing_session_id,
                ChatSession.user_id == user.id,
                ChatSession.domain_id == domain_id
            ).first()
            
            if session:
                return session, False  # Existing session found
        
        # If no session_id provided or session not found, get the most recent session for this user/domain
        recent_session = db.query(ChatSession).filter(
            ChatSession.user_id == user.id,
            ChatSession.domain_id == domain_id
        ).order_by(ChatSession.created_at.desc()).first()
        
        # If there's a recent session (within last 24 hours), reuse it
        if recent_session:
            from datetime import datetime, timedelta
            if datetime.now() - recent_session.created_at.replace(tzinfo=None) < timedelta(hours=24):
                return recent_session, False
        
        # Create new session if none exists or too old
        session = ChatSession(user_id=user.id, domain_id=domain_id)
        db.add(session)
        db.commit()
        db.refresh(session)
        return session, True  # New session created
        
    except Exception as e:
        db.rollback()
        print(f"[chat] Session management failed: {e}")
        # Return dummy session to prevent crashes
        session = ChatSession(id=-1, user_id=user.id, domain_id=domain_id)
        return session, True

def _save_message_to_session(
    db: Session,
    session: ChatSession,
    user: User,
    question: str,
    answer: str
) -> ChatMessage:
    """Save message to existing session"""
    try:
        message = ChatMessage(
            session_id=session.id,
            user_id=user.id,
            question=question,
            answer=answer,
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message
    except Exception as e:
        db.rollback()
        print(f"[chat] Message save failed: {e}")
        # Return dummy message to prevent crashes
        return ChatMessage(id=-1, session_id=session.id, user_id=user.id, question=question, answer=answer)

def _save_chat_interaction(
    db: Session, 
    user: User, 
    domain_id: int, 
    question: str, 
    answer: str
) -> tuple[ChatSession, ChatMessage]:
    """
    Legacy function for backward compatibility - creates new session every time
    Use _get_or_create_session + _save_message_to_session instead for session continuity
    """
    try:
        # Create new chat session
        session = ChatSession(user_id=user.id, domain_id=domain_id)
        db.add(session)
        db.commit()
        db.refresh(session)

        # Create chat message
        message = ChatMessage(
            session_id=session.id,
            user_id=user.id,
            question=question,
            answer=answer,
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        return session, message
    except Exception as e:
        db.rollback()
        print(f"[chat] Database save failed: {e}")
        # Return dummy objects to prevent crashes
        session = ChatSession(id=-1, user_id=user.id, domain_id=domain_id)
        message = ChatMessage(id=-1, session_id=-1, user_id=user.id, question=question, answer=answer)
        return session, message

# ---------- Routes ----------
@router.get("/chat/debug_env")
def debug_env():
    return {
        "has_openai_api_key": bool(os.getenv("OPENAI_API_KEY")),
        "llm_model": os.getenv("LLM_MODEL"),
        "openai_base_url": os.getenv("OPENAI_BASE_URL"),
    }

@router.get("/chat/domain_info")
def get_domain_info(principal = Depends(get_current_principal)):
    """Get information about user's domain access"""
    return {
        "user_domain_id": principal.domain_id,
        "user_role": principal.role,
        "domain_name": _get_domain_scope_name(principal.domain_id, principal.role == "super_admin"),
        "can_access_all_domains": principal.role == "super_admin",
        "search_scope": "global" if principal.role == "super_admin" and principal.domain_id is None else f"domain_{principal.domain_id}"
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

    # Determine search scope based on user role and domain
    search_domain_id = None
    domain_scope = "global"
    
    if principal.role == "super_admin":
        if principal.domain_id is None:
            search_domain_id = None  # Global search
            domain_scope = "global"
        else:
            search_domain_id = principal.domain_id  # Domain-specific search
            domain_scope = f"domain_{principal.domain_id}"
    else:
        if principal.domain_id is None:
            raise HTTPException(status_code=403, detail="User has no assigned domain")
        search_domain_id = principal.domain_id
        domain_scope = f"domain_{principal.domain_id}"

    # Get or create session - THIS IS THE KEY FIX
    session, is_new_session = _get_or_create_session(
        db, 
        user, 
        principal.domain_id or 0, 
        payload.session_id  # Pass the session_id from frontend
    )

    # Handle greetings
    greeting_lang = is_greeting(q)
    if greeting_lang:
        answer = make_greeting_response(greeting_lang)
        message = _save_message_to_session(db, session, user, q, answer)
        return ChatAnswer(
            answer=answer, 
            sources=[], 
            session_id=session.id, 
            message_id=message.id,
            domain_scope=domain_scope,
            is_new_session=is_new_session
        )

    # Detect user language for possible localized fallbacks
    user_lang = detect_language(q)

    # Perform domain-scoped vector search
    try:
        if search_domain_id is None:
            raw = vectordb.search_similar(q, payload.k)
        else:
            raw = vectordb.search_similar_for_domain(q, search_domain_id, payload.k)
    except Exception as e:
        print(f"[chat] Vector search failed: {e}")
        raise HTTPException(status_code=500, detail="Search service unavailable")

    hits = [_normalize_hit(h) for h in (raw or []) if h is not None]

    # Handle no results found
    if not hits or not any((h.get("page_content") or "").strip() for h in hits):
        answer = localized_not_found(user_lang)
        message = _save_message_to_session(db, session, user, q, answer)
        return ChatAnswer(
            answer=answer, 
            sources=[], 
            session_id=session.id, 
            message_id=message.id,
            domain_scope=domain_scope,
            is_new_session=is_new_session
        )

    # Generate answer from domain-specific context
    context = _build_context(hits)
    domain_name = _get_domain_scope_name(search_domain_id, principal.role == "super_admin")
    answer = _answer_with_openai(context, q, domain_name) or "I couldn't find this in the knowledge base."

    # If the model/stub returned the fallback phrase, localize it
    if (answer or "").strip() == "I couldn't find this in the knowledge base.":
        answer = localized_not_found(user_lang)

    # Save message to existing session
    message = _save_message_to_session(db, session, user, q, answer)

    return ChatAnswer(
        answer=answer, 
        sources=_extract_sources(hits), 
        session_id=session.id, 
        message_id=message.id,
        domain_scope=domain_scope,
        is_new_session=is_new_session
    )


# ---------- Session Management Endpoints ----------
@router.post("/chat/new_session")
def create_new_chat_session(
    db: Session = Depends(get_db),
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db)
):
    """Explicitly create a new chat session"""
    try:
        session = ChatSession(user_id=user.id, domain_id=principal.domain_id or 0)
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return {
            "session_id": session.id,
            "domain_id": session.domain_id,
            "domain_name": _get_domain_scope_name(session.domain_id),
            "created_at": session.created_at,
            "message": "New chat session created"
        }
    except Exception as e:
        db.rollback()
        print(f"[new_session] Failed to create session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create new session")

@router.get("/chat/current_session/{session_id}")
def get_current_session_info(
    session_id: int,
    db: Session = Depends(get_db),
    principal = Depends(get_current_principal)
):
    """Get information about current session"""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Security check
    if principal.role != "super_admin":
        if session.user_id != principal.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        if principal.domain_id is not None and session.domain_id != principal.domain_id:
            raise HTTPException(status_code=403, detail="Domain access denied")
    
    message_count = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).count()
    
    return {
        "session_id": session.id,
        "domain_id": session.domain_id,
        "domain_name": _get_domain_scope_name(session.domain_id),
        "created_at": session.created_at,
        "message_count": message_count,
        "is_active": True
    }


# ---------- Chat History Endpoints ----------
@router.get("/chat/sessions/{user_id}")
def get_user_chat_sessions(
    user_id: int, 
    db: Session = Depends(get_db),
    principal = Depends(get_current_principal)
):
    """Get all chat sessions for a user (with domain filtering for non-super_admin)"""
    
    # Security check: users can only access their own sessions unless they're super_admin
    if principal.role != "super_admin" and principal.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = db.query(ChatSession).filter(ChatSession.user_id == user_id)
    
    # Domain filtering for non-super_admin users
    if principal.role != "super_admin" and principal.domain_id is not None:
        query = query.filter(ChatSession.domain_id == principal.domain_id)
    
    sessions = query.order_by(ChatSession.created_at.desc()).all()
    return sessions

@router.get("/chat/messages/{session_id}")
def get_chat_messages(
    session_id: int, 
    db: Session = Depends(get_db),
    principal = Depends(get_current_principal)
):
    """Get all messages for a specific chat session (with security checks)"""
    
    # Get the session first to check ownership and domain
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Security checks
    if principal.role != "super_admin":
        if session.user_id != principal.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        if principal.domain_id is not None and session.domain_id != principal.domain_id:
            raise HTTPException(status_code=403, detail="Domain access denied")
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.asc()).all()
    
    return messages

@router.get("/chat/history/{user_id}")
def get_user_chat_history(
    user_id: int, 
    limit: int = 50, 
    db: Session = Depends(get_db),
    principal = Depends(get_current_principal)
):
    """Get recent chat history for a user with pagination and domain filtering"""
    
    # Security check
    if principal.role != "super_admin" and principal.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get recent sessions with domain filtering
    query = db.query(ChatSession).filter(ChatSession.user_id == user_id)
    
    if principal.role != "super_admin" and principal.domain_id is not None:
        query = query.filter(ChatSession.domain_id == principal.domain_id)
    
    sessions = query.order_by(ChatSession.created_at.desc()).limit(limit).all()
    
    history = []
    for session in sessions:
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id
        ).order_by(ChatMessage.created_at.asc()).all()
        
        history.append({
            "session_id": session.id,
            "domain_id": session.domain_id,
            "domain_name": _get_domain_scope_name(session.domain_id),
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

# ---------- Domain-specific utilities ----------
@router.get("/chat/domain_stats")
def get_domain_chat_stats(
    db: Session = Depends(get_db),
    principal = Depends(get_current_principal)
):
    """Get chat statistics for current user's domain"""
    
    if principal.domain_id is None and principal.role != "super_admin":
        raise HTTPException(status_code=403, detail="No domain assigned")
    
    if principal.role == "super_admin":
        # Super admin can see global stats
        total_sessions = db.query(ChatSession).count()
        total_messages = db.query(ChatMessage).count()
        domain_filter = None
    else:
        # Regular users see their domain stats only
        total_sessions = db.query(ChatSession).filter(
            ChatSession.domain_id == principal.domain_id
        ).count()
        total_messages = db.query(ChatMessage).join(ChatSession).filter(
            ChatSession.domain_id == principal.domain_id
        ).count()
        domain_filter = principal.domain_id
    
    return {
        "domain_id": domain_filter,
        "domain_name": _get_domain_scope_name(domain_filter, principal.role == "super_admin"),
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "user_role": principal.role
    }