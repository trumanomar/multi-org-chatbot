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

# Vector search helpers
from app.VectorDB import DB as vectordb
from app.GraphDB.graph_integration import GraphRAGIntegration
from app.utilis.greetings import (
    is_greeting,
    detect_language,
    make_greeting_response,
    localized_not_found,
)

# MySQL MCP Client
from app.MCP.mysql_mcp_client import MySQLMCPClient

# Query Router (removed format_mysql_results import to avoid conflicts)
from app.MCP.query_router import QueryRouter, DataSource, route_mysql_query

# OpenAI-compatible SDK
from openai import OpenAI

router = APIRouter(tags=["Chat"])

# Initialize clients
mysql_client = MySQLMCPClient()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
query_router = QueryRouter(openai_client)

# Safe format_mysql_results function (local to avoid import issues)
def format_mysql_results(results: List[Dict[str, Any]]) -> str:
    """Safely format MySQL results into a readable string. Handles lists of dicts."""
    print(f"[FORMAT_MYSQL] Input type: {type(results)}, len: {len(results) if hasattr(results, '__len__') else 'N/A'}")
    if not results:
        return "No records found in database."
    
    try:
        formatted = []
        for row in results:
            print(f"[FORMAT_MYSQL] Row type: {type(row)}")
            if isinstance(row, dict):
                row_str = " | ".join([f"{k}: {v}" for k, v in row.items()])
                formatted.append(row_str)
            else:
                formatted.append(str(row))
        output = "\n".join(formatted)
        print(f"[FORMAT_MYSQL] Output: {output}")
        return output
    except Exception as e:
        print(f"[FORMAT_MYSQL] Error formatting: {e}")
        return "Error formatting database results."

# Debug: Print DataSource values for troubleshooting
print(f"🔧 DataSource values - MYSQL: '{DataSource.MYSQL.value}', VECTOR: '{DataSource.VECTOR.value}', GRAPH: '{DataSource.GRAPH.value}'")

# ---------- Schemas ----------
class ChatQuery(BaseModel):
    message: str = Field(..., description="User question")
    k: int = Field(5, ge=1, le=50, description="Top-K retrieved chunks")
    session_id: int = Field(None, description="Existing session ID to continue conversation")
    answer: str = Field(None, description="Pre-generated answer (optional)")

class ChatSeparateResponse(BaseModel):
    query: str
    vector: List[Dict[str, Any]]
    graph: List[Dict[str, Any]]
    mysql: List[Dict[str, Any]] = Field(default=[])
    vector_total: int
    graph_total: int
    mysql_total: int = Field(default=0)
    session_id: int
    message_id: int
    domain_scope: str
    is_new_session: bool
    is_greeting: bool = Field(default=False)
    answer: str = Field(default="")
    sources: List[Dict[str, str]] = Field(default=[])
    routing_info: Dict[str, Any] = Field(default={})

# ---------- Enhanced System Prompt ----------
SYSTEM_INSTRUCTIONS = """You are a helpful assistant with access to multiple data sources:

📊 **MySQL Database** - Structured data (user counts, statistics, chat history, feedback)
📄 **Document Database** - Document content and text chunks  
🕸️ **Knowledge Graph** - Relationships between entities

When answering:
- Use the appropriate source based on the question type
- For statistics/counts → Use MySQL results
- For document content/explanations → Use Vector results
- For relationships → Use Graph results
- Be clear, factual, and concise
- If the answer isn't in the context, say: "I couldn't find this in the knowledge base"
- Do NOT include raw source tags or file paths
- If NO context is provided from any source, respond: "I couldn't find relevant information in the available data sources (Vector DB, Knowledge Graph, MySQL). Please rephrase or provide more details."
- NEVER invent facts, numbers, or relationships—stick strictly to the provided context.

The system has intelligently routed your query to the most relevant source(s)."""

# ---------- Helper Functions ----------
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
    if domain_id is None:
        domain_id = 0
    
    try:
        if existing_session_id:
            session = db.query(ChatSession).filter(
                ChatSession.id == existing_session_id,
                ChatSession.user_id == user.id
            ).first()
            
            if session:
                return session, False
        
        session = ChatSession(user_id=user.id, domain_id=domain_id)
        db.add(session)
        db.flush()
        db.commit()
        db.refresh(session)
        return session, True
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

def _save_message_to_session(
    db: Session,
    session: ChatSession,
    user: User,
    question: str,
    answer: str
) -> ChatMessage:
    """Save message to session"""
    if not session or not session.id or session.id <= 0:
        raise HTTPException(status_code=500, detail="Invalid session")
    
    try:
        message = ChatMessage(
            session_id=session.id,
            user_id=user.id,
            question=question,
            answer=answer,
        )
        db.add(message)
        db.flush()
        db.commit()
        db.refresh(message)
        return message
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

def _save_chat_sources(db: Session, message_id: int, sources: List[Dict[str, str]]) -> None:
    """Save sources for a chat message"""
    if not message_id or message_id <= 0:
        return
    
    try:
        for s in sources:
            src_file = (s.get("source_file") or s.get("source") or "").strip()
            snippet = (s.get("snippet") or "").strip()
            if not src_file:
                continue
            db.add(ChatSource(message_id=message_id, source=src_file, snippet=snippet))
        db.commit()
    except Exception as e:
        db.rollback()

def _build_context_components(
    query: str,
    vector_results: list,
    graph_results: list,
    mysql_results: list,
    routing_info: Dict
) -> Dict[str, Any]:
    """Builds shared context string and metadata for prompts and judge."""
    # Build comprehensive context
    context_parts = []

    # MySQL Database context
    if mysql_results:
        context_parts.append("=== DATABASE INFORMATION ===")
        mysql_formatted = format_mysql_results(mysql_results)
        context_parts.append(mysql_formatted)
        print(f"📊 [MYSQL_FORMATTED] {mysql_formatted}")

    # Combined Vector + Graph context (show together)
    if vector_results or graph_results:
        context_parts.append("\n=== SEMANTIC & RELATIONAL CONTENT ===")
        if vector_results:
            for i, v in enumerate(vector_results[:3], 1):
                content = v.get("page_content") or v.get("content") or ""
                metadata = v.get("metadata", {})
                source = metadata.get("source", "Unknown")
                context_parts.append(f"[Vector Doc {i} - {source}]\n{content}")
        if graph_results:
            for i, g in enumerate(graph_results[:3], 1):
                content = g.get("page_content") or g.get("content") or ""
                context_parts.append(f"[Graph Rel {i}]\n{content}")

    context_str = "\n\n".join(context_parts)[:4000]

    primary_source = routing_info.get("primary_source", "unknown")
    if hasattr(primary_source, 'value'):
        primary_source = primary_source.value

    available_sources = ', '.join([
        s for s, data in [
            ('MySQL', bool(mysql_results)),
            ('Vector+Graph', bool(vector_results or graph_results))
        ] if data
    ])

    return {
        "context_str": context_str,
        "primary_source": primary_source,
        "available_sources": available_sources
    }

def _generate_answer_with_llm(
    query: str,
    vector_results: list,
    graph_results: list,
    mysql_results: list,
    routing_info: Dict
) -> str:
    """Generate answer using all available context sources"""
    try:
        # Check for empty context
        total_context_items = len([r for r in [mysql_results, vector_results, graph_results] if r])
        if total_context_items == 0:
            return "I couldn't find relevant information in the available data sources (Vector DB, Knowledge Graph, MySQL). Please rephrase or provide more details."

        components = _build_context_components(
            query, vector_results, graph_results, mysql_results, routing_info
        )

        user_prompt = f"""Query Routing:
- Primary Source: {components['primary_source']}
- Confidence: {routing_info.get('confidence', 0):.2f}
- Reasoning: {routing_info.get('reasoning', 'N/A')}

Available Context Sources: {components['available_sources']}
If context is limited, note that in your response.

Context:
{components['context_str']}

User Question: {query}

Please provide a clear answer based on the context above."""

        print(f"🧭 [ROUTING] Primary: {components['primary_source']}, Confidence: {routing_info.get('confidence', 0):.2f}")
        print(f"📝 [CONTEXT] Length: {len(components['context_str'])} chars")

        response = openai_client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "llama3.1:8b-instruct-q4_K_M"),
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

        answer = response.choices[0].message.content.strip()
        return answer

    except Exception as e:
        print(f"[LLM] Generation failed: {e}")
        import traceback
        print(f"[LLM] Full traceback: {traceback.format_exc()}")
        return "I couldn't generate an answer due to an internal error."

def _judge_answer_with_llm(
    question: str,
    answer: str,
    context_str: str,
    primary_source: str
) -> Dict[str, Any]:
    """Use LLM as a judge to evaluate answer quality. Prints JSON to console and returns it."""
    try:
        judge_instructions = (
            "You are a strict evaluator. Score the assistant's answer against the user's question and the provided context."
            " Return a compact JSON object with fields: relevance (0-1), groundedness (0-1), completeness (0-1),"
            " correctness (0-1), follows_routing (0-1), issues (short array of strings), and verdict ('pass'|'fail')."
            " Definitions: relevance=how well it addresses the question; groundedness=backed by context; completeness=covers key points;"
            " correctness=factually correct per context; follows_routing=uses the primary source {primary_source} when appropriate."
            " If context is empty, set groundedness=0 and add issue 'no context provided'."
        )

        user_block = (
            f"Context:\n{context_str[:4000]}\n\n"
            f"Question: {question}\n\n"
            f"Assistant Answer: {answer}"
        )

        response = openai_client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "llama3.1:8b-instruct-q4_K_M"),
            messages=[
                {"role": "system", "content": judge_instructions},
                {"role": "user", "content": user_block},
            ],
            temperature=0.0,
        )

        raw = response.choices[0].message.content.strip()
        try:
            report = json.loads(raw)
        except Exception:
            # Attempt to extract JSON if model added prose
            start = raw.find('{')
            end = raw.rfind('}')
            report = json.loads(raw[start:end+1]) if start != -1 and end != -1 else {
                "relevance": None,
                "groundedness": None,
                "completeness": None,
                "correctness": None,
                "follows_routing": None,
                "issues": ["Could not parse judge output"],
                "verdict": "fail"
            }

        print("🧑\u200d⚖️ [JUDGE] " + json.dumps(report, ensure_ascii=False))
        return report
    except Exception as e:
        print(f"[JUDGE] Evaluation failed: {e}")
        import traceback
        print(f"[JUDGE] Full traceback: {traceback.format_exc()}")
        return {
            "relevance": None,
            "groundedness": None,
            "completeness": None,
            "correctness": None,
            "follows_routing": None,
            "issues": ["judge error"],
            "verdict": "fail"
        }

# ---------- Main Chat Endpoint ----------
@router.post("/chat/query_separate", response_model=ChatSeparateResponse)
async def chat_query_separate(
    payload: ChatQuery,
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db),
    db: Session = Depends(get_db)
):
    """
    Enhanced chat endpoint with intelligent routing
    Automatically routes queries to Vector, Graph, or MySQL based on content
    """
    q = (payload.message or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty message")

    # Determine search scope
    search_domain_id = None
    domain_scope = "global"
    
    if principal.role == "super_admin":
        if principal.domain_id is None:
            search_domain_id = None
            domain_scope = "global"
        else:
            search_domain_id = principal.domain_id
            domain_scope = f"domain_{principal.domain_id}"
    else:
        if principal.domain_id is None:
            raise HTTPException(status_code=403, detail="User has no assigned domain")
        search_domain_id = principal.domain_id
        domain_scope = f"domain_{principal.domain_id}"

    print(f"🔍 Using domain_id: {search_domain_id} (scope: {domain_scope})")

    # Get or create session
    session, is_new_session = _get_or_create_session(
        db, user, principal.domain_id or 0, payload.session_id
    )

    # Handle greetings
    greeting_lang = is_greeting(q)
    if greeting_lang:
        answer = make_greeting_response(greeting_lang)
        message = _save_message_to_session(db, session, user, q, answer)
        
        return ChatSeparateResponse(
            query=q,
            vector=[], graph=[], mysql=[],
            vector_total=0, graph_total=0, mysql_total=0,
            session_id=session.id, message_id=message.id,
            domain_scope=domain_scope, is_new_session=is_new_session,
            is_greeting=True, answer=answer, sources=[],
            routing_info={"primary_source": "greeting", "confidence": 1.0}
        )

    # 🧭 STEP 1: Route the query intelligently
    print(f"\n{'='*60}")
    print(f"🔍 Query: {q}")
    routing = query_router.route_query(q, use_llm=True)
    print(f"🧭 Routing Decision:")
    print(f"   Primary: {routing['primary_source'].value if hasattr(routing['primary_source'], 'value') else routing['primary_source']}")
    print(f"   Secondary: {[s.value if hasattr(s, 'value') else s for s in routing.get('secondary_sources', [])]}")
    print(f"   Confidence: {routing['confidence']:.2f}")
    print(f"   Reasoning: {routing['reasoning']}")
    print(f"{'='*60}\n")

    # Initialize results
    vector_results = []
    graph_results = []
    mysql_results = []
    vector_total = 0
    graph_total = 0
    mysql_total = 0

    k = payload.k or 5
    graph = GraphRAGIntegration()
    
    # Determine which sources to query
    primary = routing["primary_source"]
    secondary = routing.get("secondary_sources", [])
    all_sources = [primary] + secondary

    # Conditionally include vector and graph only if primary is not 'mysql'
    primary_value = primary.value if hasattr(primary, 'value') else primary
    if primary_value != 'mysql':
        if 'vector' not in [s.value if hasattr(s, 'value') else s for s in all_sources] and 'generative' not in [s.value if hasattr(s, 'value') else s for s in all_sources]:
            all_sources.append('vector')
        if 'graph' not in [s.value if hasattr(s, 'value') else s for s in all_sources]:
            all_sources.append('graph')
    print(f"🔍 Final sources to query: {all_sources}")

    # 🔍 STEP 2: Execute queries based on routing
    for source in all_sources:
        source_value = source.value if hasattr(source, 'value') else source
        print(f"   Executing source: '{source_value}' (type: {type(source_value)})")
        
        # MySQL Query - Use string comparison
        if source_value == 'mysql':
            print(f"💾 Querying MySQL for '{q}' in domain {search_domain_id}...")
            try:
                mysql_result = route_mysql_query(q, mysql_client, search_domain_id or 0, user.id)
                print(f"   MySQL raw result: {json.dumps(mysql_result, indent=2)[:500]}...")
                if mysql_result.get("success"):
                    mysql_results = mysql_result.get("data", [])
                    mysql_total = len(mysql_results)
                    print(f"   ✅ Found {mysql_total} MySQL records")
                    if mysql_total == 0:
                        print(f"   ⚠️  Empty MySQL: Check SQL generation or data in domain {search_domain_id}")
                else:
                    print(f"   ❌ MySQL failed: {mysql_result.get('error', 'Unknown')}")
            except Exception as e:
                print(f"   ❌ MySQL error: {e}")
        
        # Vector Query - Use string comparison
        if source_value == 'vector' or source_value == 'generative':
            print(f"📄 Querying Vector DB for '{q}' in domain {search_domain_id}...")
            try:
                vector_part = await graph.query_vector(
                    q, 
                    domain_id=search_domain_id or 0, 
                    k=k
                )
                print(f"   Vector raw: total_found={vector_part.get('total_found')}, results_len={len(vector_part.get('results', []))}")
                vector_results = vector_part.get("results") or []
                vector_total = int(vector_part.get("total_found") or 0)
                print(f"   ✅ Found {vector_total} vector results")
                if vector_total == 0:
                    print(f"   ⚠️  Empty Vector: Check embeddings/index for domain {search_domain_id}")
            except Exception as e:
                print(f"   ❌ Vector error: {e}")
        
        # Graph Query - Use string comparison with enhanced logging
        if source_value == 'graph':
            print(f"🕸️  Querying Graph DB for '{q}' in domain {search_domain_id}...")
            try:
                # Log the exact params passed to query_graph
                print(f"   Graph params: query='{q}', domain_id={search_domain_id or 0}, max_results={k}")
                graph_part = await graph.query_graph(
                    q, 
                    domain_id=search_domain_id or 0, 
                    max_results=k
                )
                print(f"   Graph raw: total_found={graph_part.get('total_found')}, results_len={len(graph_part.get('results', []))}")
                # Log first result content for debugging
                if graph_part.get('results'):
                    first_content = graph_part['results'][0].get('content', 'N/A')[:100] + '...'
                    print(f"   Graph first result preview: {first_content}")
                graph_results = graph_part.get("results") or []
                graph_total = int(graph_part.get("total_found") or 0)
                print(f"   ✅ Found {graph_total} graph results")
                if graph_total == 0:
                    print(f"   ⚠️  Empty Graph: Check graph nodes/relationships for domain {search_domain_id}")
            except Exception as e:
                print(f"   ❌ Graph error: {e}")

    # Extract sources from vector results
    sources = []
    seen_sources = set()
    for result in vector_results[:5]:
        metadata = result.get("metadata", {})
        source_file = metadata.get("source") or metadata.get("file_path") or ""
        
        if not source_file or source_file in seen_sources:
            continue
            
        seen_sources.add(source_file)
        content = result.get("content") or result.get("page_content") or ""
        snippet = (content[:300] + "…") if len(content) > 300 else content
        title = metadata.get("title") or os.path.basename(str(source_file))
        
        sources.append({
            "source": source_file,
            "snippet": snippet,
            "title": title
        })

    # 🤖 STEP 3: Generate answer using LLM with all context
    print(f"🤖 Generating answer...")
    generated_answer = _generate_answer_with_llm(
        q, vector_results, graph_results, mysql_results, routing
    )
    print(f"   ✅ Answer generated ({len(generated_answer)} chars)\n")

    # 🧑‍⚖️ STEP 3.1: Evaluate the generated answer (prints compact JSON to console)
    try:
        components = _build_context_components(q, vector_results, graph_results, mysql_results, routing)
        _ = _judge_answer_with_llm(
            question=q,
            answer=generated_answer,
            context_str=components.get("context_str", ""),
            primary_source=components.get("primary_source", "unknown")
        )
    except Exception as e:
        print(f"[JUDGE] Skipped due to error: {e}")

    # Save message to database
    message = _save_message_to_session(db, session, user, q, generated_answer)
    message.vector_results = json.dumps(vector_results)
    message.graph_results = json.dumps(graph_results)
    db.commit()

    # Save sources
    if sources and message.id:
        _save_chat_sources(db, message.id, sources)

    return ChatSeparateResponse(
        query=q,
        vector=vector_results,
        graph=graph_results,
        mysql=mysql_results,
        vector_total=vector_total,
        graph_total=graph_total,
        mysql_total=mysql_total,
        session_id=session.id,
        message_id=message.id,
        domain_scope=domain_scope,
        is_new_session=is_new_session,
        is_greeting=False,
        answer=generated_answer,
        sources=sources,
        routing_info={
            "primary_source": routing["primary_source"].value if hasattr(routing["primary_source"], "value") else routing["primary_source"],
            "secondary_sources": [s.value if hasattr(s, "value") else s for s in routing.get("secondary_sources", [])],
            "confidence": routing["confidence"],
            "reasoning": routing["reasoning"]
        }
    )

# ---------- Other Endpoints (unchanged) ----------
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
        raise HTTPException(status_code=500, detail="Failed to create new session")

@router.get("/chat/messages/{session_id}")
def get_chat_messages(
    session_id: int, 
    db: Session = Depends(get_db),
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db)
):
    """Get all messages for a session with their sources"""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if principal.role != "super_admin":
        if session.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        if principal.domain_id is not None and session.domain_id != principal.domain_id:
            raise HTTPException(status_code=403, detail="Domain access denied")
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.asc()).all()
    
    result = []
    for msg in messages:
        sources = db.query(ChatSource).filter(ChatSource.message_id == msg.id).all()
        
        result.append({
            "id": msg.id,
            "question": msg.question,
            "answer": msg.answer,
            "vector": json.loads(msg.vector_results or "[]"),
            "graph": json.loads(msg.graph_results or "[]"),
            "created_at": msg.created_at,
            "sources": [{"source": s.source, "snippet": s.snippet} for s in sources]
        })
    
    return result