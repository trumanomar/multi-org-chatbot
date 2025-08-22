from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP,Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.DB.db import Base
import enum

# --- Domain Table ---
class Domain(Base):
    __tablename__ = 'domains'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    active=Column(Boolean, default=True)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    users = relationship("User", back_populates="domain", cascade="all, delete")
    docs = relationship("Docs", back_populates="domain", cascade="all, delete")
    feedbacks = relationship("Feedback", back_populates="domain", cascade="all, delete")
    chat_sessions = relationship("ChatSession", back_populates="domain", cascade="all, delete")


# --- User Table ---
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    role_based = Column(String(50), nullable=False)
    domain_id = Column(Integer, ForeignKey('domains.id'), nullable=False)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    domain = relationship("Domain", back_populates="users")
    docs = relationship("Docs", back_populates="user", cascade="all, delete")
    chunks = relationship("Chunk", back_populates="user", cascade="all, delete")
    feedbacks = relationship("Feedback", back_populates="user", cascade="all, delete")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete")


# --- Docs Table ---
class Docs(Base):
    __tablename__ = 'docs'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    domain_id = Column(Integer, ForeignKey('domains.id'), nullable=False)
    active=Column(Boolean, default=True)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationships
    domain = relationship("Domain", back_populates="docs")
    user = relationship("User", back_populates="docs")
    chunks = relationship("Chunk", back_populates="doc", cascade="all, delete")


# --- Chunks Table ---
class Chunk(Base):
    __tablename__ = 'chunks'
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    meta_data = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    domain_id = Column(Integer, ForeignKey('domains.id'), nullable=False)
    doc_id = Column(Integer, ForeignKey('docs.id'), nullable=False)
    

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="chunks")
    doc = relationship("Docs", back_populates="chunks")
class Feedback(Base):
    __tablename__ = 'feedback'
    id = Column(Integer, primary_key=True, index=True)

    # foreign keys
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    domain_id = Column(Integer, ForeignKey('domains.id'), nullable=False)

    # payload
    content = Column(Text, nullable=False)
    rating = Column(Integer, nullable=False)
    question = Column(Text, nullable=False)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="feedbacks")
    domain = relationship("Domain", back_populates="feedbacks")

    @property
    def user_name(self):
        return self.user.username if self.user else None
class ChatSession(Base):
    __tablename__ = 'chat_sessions'  
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    domain_id = Column(Integer, ForeignKey('domains.id'), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    
    user = relationship("User", back_populates="chat_sessions")
    domain = relationship("Domain", back_populates="chat_sessions")
    chat_messages = relationship("ChatMessage", back_populates="chat_session", cascade="all, delete")


class ChatMessage(Base):
    __tablename__ = 'chat_messages' 
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('chat_sessions.id'), nullable=False) 
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    
    chat_session = relationship("ChatSession", back_populates="chat_messages")
    user = relationship("User", back_populates="chat_messages")


#Role
class RoleEnum(str, enum.Enum):
    super_admin = "super_admin"
    admin = "admin"
    user = "user"
