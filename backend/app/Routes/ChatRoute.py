from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Any, Dict, List
import os
from sqlalchemy.orm import Session
import json
# Database imports
from app.DB.db import get_db
from app.Models.tables import ChatSession, ChatMessage, User, ChatSource
from app.auth.dependencies import get_current_principal, get_current_user_db

# Vector search helpers (module-level)
from app.VectorDB import DB as vectordb
from app.GraphDB.graph_integration import GraphRAGIntegration
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
    answer: str = Field(None, description="Pre-generated answer (optional, for saving complete message)")

class ChatSeparateResponse(BaseModel):
    query: str
    vector: List[Dict[str, Any]]
    graph: List[Dict[str, Any]]
    vector_total: int
    graph_total: int
    session_id: int
    message_id: int
    domain_scope: str = Field(description="Domain that was searched")
    is_new_session: bool = Field(description="Whether this created a new session")
    is_greeting: bool = Field(default=False, description="Whether this was a greeting")
    answer: str = Field(default="", description="Generated answer for greetings")
    sources: List[Dict[str, str]] = Field(default=[], description="Extracted sources")

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

def _get_or_create_session(
    db: Session, 
    user: User, 
    domain_id: int,
    existing_session_id: int = None
) -> tuple[ChatSession, bool]:
    """Get existing session or create new one"""
    
    # لو domain_id فاضي، استخدم 0
    if domain_id is None:
        domain_id = 0
    
    print(f"[DEBUG] Starting session creation - user_id={user.id}, domain_id={domain_id}")
    
    try:
        # لو في session_id موجود، جيبه
        if existing_session_id:
            session = db.query(ChatSession).filter(
                ChatSession.id == existing_session_id,
                ChatSession.user_id == user.id
            ).first()
            
            if session:
                print(f"[SUCCESS] Found existing session: {session.id}")
                return session, False
        
        # اعمل session جديد
        session = ChatSession(user_id=user.id, domain_id=domain_id)
        db.add(session)
        db.flush()  # مهم جداً - علشان تجيب الـ ID قبل الـ commit
        print(f"[DEBUG] Session created with ID: {session.id}")
        db.commit()
        db.refresh(session)
        print(f"[SUCCESS] Session committed successfully: {session.id}")
        return session, True
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Session creation failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def _save_message_to_session(
    db: Session,
    session: ChatSession,
    user: User,
    question: str,
    answer: str
) -> ChatMessage:
    """Save message to session"""
    
    print(f"[DEBUG] Saving message - session_id={session.id}, user_id={user.id}")
    
    # تأكد إن الـ session صالح
    if not session or not session.id or session.id <= 0:
        print(f"[ERROR] Invalid session ID: {session.id if session else 'None'}")
        raise HTTPException(status_code=500, detail="Invalid session")
    
    try:
        message = ChatMessage(
            session_id=session.id,
            user_id=user.id,
            question=question,
            answer=answer,
        )
        db.add(message)
        db.flush()  # مهم جداً
        print(f"[DEBUG] Message created with ID: {message.id}")
        db.commit()
        db.refresh(message)
        print(f"[SUCCESS] Message saved: {message.id}")
        return message
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Message save failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def _save_chat_sources(db: Session, message_id: int, sources: List[Dict[str, str]]) -> None:
    """Save sources for a chat message"""
    if not message_id or message_id <= 0:
        print(f"[chat] ⚠️ Skipping source save - invalid message_id: {message_id}")
        return
    
    try:
        for s in sources:
            src_file = (s.get("source_file") or s.get("source") or "").strip()
            snippet = (s.get("snippet") or "").strip()
            if not src_file:
                continue
            db.add(ChatSource(message_id=message_id, source=src_file, snippet=snippet))
        db.commit()
        print(f"[chat] ✅ Saved {len(sources)} sources for message {message_id}")
    except Exception as e:
        db.rollback()
        print(f"[chat] ❌ Failed to save sources for message {message_id}: {e}")
        # Don't raise - sources are optional
def _generate_answer_with_llm(query: str, vector_results: list, graph_results: list) -> str:
    """Generate final answer from LLM using vector + graph context"""
    try:
        client = OpenAI()

        # Collect context from vector + graph
        context_texts = []
        for v in vector_results:
            context_texts.append(v.get("page_content") or v.get("content") or "")
        for g in graph_results:
            context_texts.append(g.get("page_content") or g.get("content") or "")

        context_str = "\n".join(context_texts)[:4000]  # truncate for safety

        # Debug: print context to logs
        print("[DEBUG] Context passed to LLM:\n", context_str[:1000], "..." if len(context_str) > 1000 else "")

        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                {
                    "role": "user",
                    "content": f"Here is the context extracted from the knowledge base:\n\n{context_str}\n\n"
                               f"User question: {query}\n\nPlease provide a clear and factual answer "
                               f"based only on the context above."
                },
            ],
            temperature=0,
        )

        answer = response.choices[0].message.content.strip()
        return answer

    except Exception as e:
        print(f"[chat] ❌ LLM generation failed: {e}")
        return "I couldn't generate an answer due to an internal error."

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

@router.post("/chat/query_separate", response_model=ChatSeparateResponse)
async def chat_query_separate(
    payload: ChatQuery,
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db),
    db: Session = Depends(get_db)
):
    """
    Main chat endpoint - handles both greetings and queries
    Returns separate vector and graph results along with saved message info
    """
    q = (payload.message or "").strip()
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

    # Get or create session
    session, is_new_session = _get_or_create_session(
        db, 
        user, 
        principal.domain_id or 0, 
        payload.session_id
    )

    # Handle greetings
    greeting_lang = is_greeting(q)
    if greeting_lang:
        answer = make_greeting_response(greeting_lang)
        message = _save_message_to_session(db, session, user, q, answer)
        
        return ChatSeparateResponse(
            query=q,
            vector=[],
            graph=[],
            vector_total=0,
            graph_total=0,
            session_id=session.id,
            message_id=message.id,
            domain_scope=domain_scope,
            is_new_session=is_new_session,
            is_greeting=True,
            answer=answer,
            sources=[]
        )

    # Perform queries
    k = payload.k or 5
    graph = GraphRAGIntegration()
    
    # Query vector and graph databases
    if search_domain_id is None:
        vector_part = await graph.query_vector(q, domain_id=0, k=k)
        graph_part = await graph.query_graph(q, domain_id=0, max_results=k)
    else:
        vector_part = await graph.query_vector(q, domain_id=search_domain_id, k=k)
        graph_part = await graph.query_graph(q, domain_id=search_domain_id, max_results=k)

    # Extract results
    vector_results = vector_part.get("results") or []
    graph_results = graph_part.get("results") or []
    vector_total = int(vector_part.get("total_found") or 0)
    graph_total = int(graph_part.get("total_found") or 0)

    # Prepare sources from vector results
    sources = []
    seen_sources = set()
    for result in vector_results[:5]:  # Top 5 sources
        metadata = result.get("metadata", {})
        source_file = metadata.get("source") or metadata.get("file_path") or metadata.get("filename") or ""
        
        if not source_file or source_file in seen_sources:
            continue
            
        seen_sources.add(source_file)
        content = result.get("content") or result.get("page_content") or ""
        snippet = (content[:300] + "…") if len(content) > 300 else content
        title = metadata.get("title") or metadata.get("doc_name") or os.path.basename(str(source_file))
        
        sources.append({
            "source": source_file,
            "snippet": snippet,
            "title": title
        })

    # Save message to session
    # Use provided answer if available, otherwise empty string
   # --- Generate answer using LLM ---
    generated_answer = _generate_answer_with_llm(q, vector_results, graph_results)

    # Save message with generated answer
    message = _save_message_to_session(db, session, user, q, generated_answer)
    message.vector_results = json.dumps(vector_results)
    message.graph_results = json.dumps(graph_results)
    db.commit()
 


    # Save sources if we have them
    if sources and message.id:
        _save_chat_sources(db, message.id, sources)

    return ChatSeparateResponse(
        query=q,
        
        vector_total=vector_total,
        graph_total=graph_total,
        session_id=session.id,
        message_id=message.id,
        domain_scope=domain_scope,
        is_new_session=is_new_session,
        is_greeting=False,
        answer=generated_answer,
        vector=vector_results,
        graph=graph_results,
        sources=sources
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
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db)
):
    """Get information about current session"""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Security check
    if principal.role != "super_admin":
        if session.user_id != user.id:
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

@router.get("/chat/sessions/{user_id}")
def get_user_chat_sessions(
    user_id: int, 
    db: Session = Depends(get_db),
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db)
):
    """Get all chat sessions for a user"""
    # Security check: users can only access their own sessions unless they're super_admin
    if principal.role != "super_admin" and user.id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = db.query(ChatSession).filter(ChatSession.user_id == user_id)
    
    # Domain filtering for non-super_admin users
    if principal.role != "super_admin" and principal.domain_id is not None:
        query = query.filter(ChatSession.domain_id == principal.domain_id)
    
    sessions = query.order_by(ChatSession.created_at.desc()).all()
    
    return [{
        "session_id": s.id,
        "domain_id": s.domain_id,
        "domain_name": _get_domain_scope_name(s.domain_id),
        "created_at": s.created_at
    } for s in sessions]

@router.get("/chat/messages/{session_id}")
def get_chat_messages(
    session_id: int, 
    db: Session = Depends(get_db),
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db)
):
    """Get all messages for a session with their sources"""
    
    # Get the session first to check ownership and domain
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Security checks
    if principal.role != "super_admin":
        if session.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        if principal.domain_id is not None and session.domain_id != principal.domain_id:
            raise HTTPException(status_code=403, detail="Domain access denied")
    
    # Get messages with their sources
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.asc()).all()
    
    result = []
    for msg in messages:
        # Get sources for this message
        sources = db.query(ChatSource).filter(
            ChatSource.message_id == msg.id
        ).all()
        
        result.append({
            "id": msg.id,
            "question": msg.question,
            "answer": msg.answer,
            "vector": json.loads(msg.vector_results or "[]"),
            "graph": json.loads(msg.graph_results or "[]"),
            "created_at": msg.created_at,
            "sources": [
                {
                    "source": s.source,
                    "snippet": s.snippet
                } for s in sources
            ]
        })
    
    return result

@router.get("/chat/history/{user_id}")
def get_user_chat_history(
    user_id: int, 
    limit: int = 50, 
    db: Session = Depends(get_db),
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db)
):
    """Get complete chat history with messages and sources"""
    
    # Security check
    if principal.role != "super_admin" and user.id != user_id:
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
        
        messages_with_sources = []
        for msg in messages:
            # Get sources for each message
            sources = db.query(ChatSource).filter(
                ChatSource.message_id == msg.id
            ).all()
            
            messages_with_sources.append({
                "id": msg.id,
                "question": msg.question,
                "answer": msg.answer,
                "vector": json.loads(msg.vector_results or "[]"),
                "graph": json.loads(msg.graph_results or "[]"),
                "created_at": msg.created_at,
                "sources": [
                    {
                        "source": s.source,
                        "snippet": s.snippet
                    } for s in sources
                ]
            })
        
        history.append({
            "session_id": session.id,
            "domain_id": session.domain_id,
            "domain_name": _get_domain_scope_name(session.domain_id),
            "created_at": session.created_at,
            "messages": messages_with_sources
        })
    
    return history

# ---------- Update Message Answer ----------
class UpdateAnswerRequest(BaseModel):
    answer: str = Field(..., description="Generated answer to save")
    vector: List[Dict[str, Any]] = Field(default=[], description="Vector results to save")
    graph: List[Dict[str, Any]] = Field(default=[], description="Graph results to save")

@router.patch("/chat/message/{message_id}/answer")
def update_message_answer(
    message_id: int,
    payload: UpdateAnswerRequest,
    db: Session = Depends(get_db),
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db)
):
    message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if principal.role != "super_admin" and message.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        message.answer = payload.answer.strip()
        message.vector_results = json.dumps(payload.vector or [])
        message.graph_results = json.dumps(payload.graph or [])
        db.commit()
        db.refresh(message)

        return {
            "message_id": message.id,
            "answer": message.answer,
            "vector": json.loads(message.vector_results or "[]"),
            "graph": json.loads(message.graph_results or "[]"),
            "updated": True,
            "message": "Answer (and context) saved successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update answer: {str(e)}")


# ---------- Bulk Update (للـ Frontend) ----------
class BulkUpdateAnswerRequest(BaseModel):
    message_id: int
    answer: str
    vector: List[Dict[str, Any]] = Field(default=[])
    graph: List[Dict[str, Any]] = Field(default=[])

@router.post("/chat/save_answer")
def save_generated_answer(
    payload: BulkUpdateAnswerRequest,
    db: Session = Depends(get_db),
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db)
):
    message = db.query(ChatMessage).filter(ChatMessage.id == payload.message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if principal.role != "super_admin" and message.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        message.answer = payload.answer.strip()
        message.vector_results = json.dumps(payload.vector or [])
        message.graph_results = json.dumps(payload.graph or [])
        db.commit()

        return {
            "success": True,
            "message_id": payload.message_id,
            "answer": message.answer,
            "vector": json.loads(message.vector_results or "[]"),
            "graph": json.loads(message.graph_results or "[]"),
            "message": "Answer (and context) saved"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save answer: {str(e)}")



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