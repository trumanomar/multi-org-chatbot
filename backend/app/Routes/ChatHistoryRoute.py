from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field

from app.DB.db import get_db
from app.Models.tables import ChatSession, ChatMessage, User, Domain
from app.auth.dependencies import get_current_principal, get_current_user_db

router = APIRouter(prefix="/chat-history", tags=["Chat History"])

# ---------- Schemas ----------
class ChatSessionResponse(BaseModel):
    id: int
    user_id: int
    domain_id: int
    created_at: str
    message_count: int
    last_message_at: Optional[str]

class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    user_id: int
    question: str
    answer: str
    created_at: str

class ChatHistoryResponse(BaseModel):
    session_id: int
    created_at: str
    messages: List[ChatMessageResponse]

class ChatAnalytics(BaseModel):
    total_sessions: int
    total_messages: int
    average_messages_per_session: float
    most_active_hours: List[int]
    recent_activity: List[dict]

# ---------- Routes ----------
@router.get("/sessions", response_model=List[ChatSessionResponse])
def get_chat_sessions(
    user_id: Optional[int] = Query(None, description="Filter by user ID (admin only)"),
    domain_id: Optional[int] = Query(None, description="Filter by domain ID (admin only)"),
    limit: int = Query(50, ge=1, le=100, description="Number of sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db),
    db: Session = Depends(get_db)
):
    """Get chat sessions with optional filtering and pagination"""
    query = db.query(ChatSession)
    
    # If user_id is specified and user is admin, allow filtering by any user
    # Otherwise, only show current user's sessions
    if user_id and principal.role in ["admin", "super_admin"]:
        query = query.filter(ChatSession.user_id == user_id)
    else:
        query = query.filter(ChatSession.user_id == user.id)
    
    # If domain_id is specified and user is admin, allow filtering by any domain
    # Otherwise, only show current user's domain
    if domain_id and principal.role in ["admin", "super_admin"]:
        query = query.filter(ChatSession.domain_id == domain_id)
    else:
        query = query.filter(ChatSession.domain_id == principal.domain_id)
    
    # Add message count and last message time
    sessions = query.order_by(desc(ChatSession.created_at)).offset(offset).limit(limit).all()
    
    result = []
    for session in sessions:
        message_count = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).count()
        last_message = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(desc(ChatMessage.created_at)).first()
        
        result.append(ChatSessionResponse(
            id=session.id,
            user_id=session.user_id,
            domain_id=session.domain_id,
            created_at=session.created_at.isoformat(),
            message_count=message_count,
            last_message_at=last_message.created_at.isoformat() if last_message else None
        ))
    
    return result

@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
def get_session_messages(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Get all messages for a specific chat session"""
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
    
    if not messages:
        raise HTTPException(status_code=404, detail="Session not found or no messages")
    
    return [ChatMessageResponse(
        id=msg.id,
        session_id=msg.session_id,
        user_id=msg.user_id,
        question=msg.question,
        answer=msg.answer,
        created_at=msg.created_at.isoformat()
    ) for msg in messages]

@router.get("/history", response_model=List[ChatHistoryResponse])
def get_user_chat_history(
    limit: int = Query(20, ge=1, le=100, description="Number of recent sessions to return"),
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db),
    db: Session = Depends(get_db)
):
    """Get recent chat history for a user"""
    # Get recent sessions
    sessions = db.query(ChatSession).filter(ChatSession.user_id == user.id).order_by(desc(ChatSession.created_at)).limit(limit).all()
    
    if not sessions:
        return []
    
    history = []
    for session in sessions:
        messages = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.asc()).all()
        
        history.append(ChatHistoryResponse(
            session_id=session.id,
            created_at=session.created_at.isoformat(),
            messages=[ChatMessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                user_id=msg.user_id,
                question=msg.question,
                answer=msg.answer,
                created_at=msg.created_at.isoformat()
            ) for msg in messages]
        ))
    
    return history

@router.get("/analytics", response_model=ChatAnalytics)
def get_user_chat_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db),
    db: Session = Depends(get_db)
):
    """Get chat analytics for a user"""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get sessions and messages within the time period
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == user.id,
        ChatSession.created_at >= cutoff_date
    ).all()
    
    session_ids = [s.id for s in sessions]
    messages = db.query(ChatMessage).filter(ChatMessage.session_id.in_(session_ids)).all()
    
    # Calculate analytics
    total_sessions = len(sessions)
    total_messages = len(messages)
    avg_messages = total_messages / total_sessions if total_sessions > 0 else 0
    
    # Most active hours (simplified)
    hour_counts = {}
    for msg in messages:
        hour = msg.created_at.hour
        hour_counts[hour] = hour_counts.get(hour, 0) + 1
    
    most_active_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    most_active_hours = [hour for hour, count in most_active_hours]
    
    # Recent activity (last 7 days)
    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent_sessions = [s for s in sessions if s.created_at >= recent_cutoff]
    recent_activity = [
        {
            "date": s.created_at.date().isoformat(),
            "session_count": 1,
            "message_count": len([m for m in messages if m.session_id == s.id])
        } for s in recent_sessions
    ]
    
    return ChatAnalytics(
        total_sessions=total_sessions,
        total_messages=total_messages,
        average_messages_per_session=round(avg_messages, 2),
        most_active_hours=most_active_hours,
        recent_activity=recent_activity
    )

@router.delete("/sessions/{session_id}")
def delete_chat_session(
    session_id: int,
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db),
    db: Session = Depends(get_db)
):
    """Delete a chat session and all its messages"""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if user can delete this session (same user or admin)
    if session.user_id != user.id and principal.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Can only delete your own sessions")
    
    # Messages will be deleted automatically due to cascade
    db.delete(session)
    db.commit()
    
    return {"message": "Session deleted successfully"}

@router.get("/search")
def search_chat_history(
    query: str = Query(..., description="Search term"),
    user_id: Optional[int] = Query(None, description="Filter by user ID (admin only)"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db),
    db: Session = Depends(get_db)
):
    """Search through chat history by question or answer content"""
    search_query = f"%{query}%"
    
    db_query = db.query(ChatMessage).filter(
        ChatMessage.question.ilike(search_query) | ChatMessage.answer.ilike(search_query)
    )
    
    # If user_id is specified and user is admin, allow filtering by any user
    # Otherwise, only search current user's messages
    if user_id and principal.role in ["admin", "super_admin"]:
        db_query = db_query.filter(ChatMessage.user_id == user_id)
    else:
        db_query = db_query.filter(ChatMessage.user_id == user.id)
    
    messages = db_query.order_by(desc(ChatMessage.created_at)).limit(limit).all()
    
    results = []
    for msg in messages:
        session = db.query(ChatSession).filter(ChatSession.id == msg.session_id).first()
        results.append({
            "message_id": msg.id,
            "session_id": msg.session_id,
            "user_id": msg.user_id,
            "question": msg.question,
            "answer": msg.answer,
            "created_at": msg.created_at.isoformat(),
            "session_created": session.created_at.isoformat() if session else None
        })
    
    return results

@router.get("/my-sessions", response_model=List[ChatSessionResponse])
def get_my_chat_sessions(
    limit: int = Query(20, ge=1, le=100, description="Number of recent sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db),
    db: Session = Depends(get_db)
):
    """Get current user's chat sessions"""
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == user.id,
        ChatSession.domain_id == principal.domain_id
    ).order_by(desc(ChatSession.created_at)).offset(offset).limit(limit).all()
    
    result = []
    for session in sessions:
        message_count = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).count()
        last_message = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(desc(ChatMessage.created_at)).first()
        
        result.append(ChatSessionResponse(
            id=session.id,
            user_id=session.user_id,
            domain_id=session.domain_id,
            created_at=session.created_at.isoformat(),
            message_count=message_count,
            last_message_at=last_message.created_at.isoformat() if last_message else None
        ))
    
    return result
