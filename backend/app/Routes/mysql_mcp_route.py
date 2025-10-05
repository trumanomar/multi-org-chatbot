"""
MySQL MCP Integration Route
Provides endpoints to integrate MySQL MCP server with the main API
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import requests
import json
import logging
from app.auth.dependencies import get_current_principal, get_current_user_db
from app.Models.tables import User
from sqlalchemy.orm import Session
from app.DB.db import get_db

router = APIRouter(tags=["MySQL MCP Integration"])
logger = logging.getLogger(__name__)

# MySQL MCP server configuration
MYSQL_MCP_BASE_URL = "http://127.0.0.1:5002"

class QueryRequest(BaseModel):
    query: str
    parameters: Optional[Dict[str, Any]] = None

class InsertRequest(BaseModel):
    table: str
    data: Dict[str, Any]

class UpdateRequest(BaseModel):
    table: str
    data: Dict[str, Any]
    where_clause: str
    where_parameters: Optional[Dict[str, Any]] = None

def _make_mysql_mcp_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make request to MySQL MCP server"""
    url = f"{MYSQL_MCP_BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, timeout=30)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error to MySQL MCP server at {url}")
        raise HTTPException(
            status_code=503, 
            detail="MySQL MCP server is not available. Make sure it's running on port 5002."
        )
    except requests.exceptions.Timeout:
        logger.error(f"Timeout error to MySQL MCP server at {url}")
        raise HTTPException(status_code=504, detail="MySQL MCP server request timeout")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error to MySQL MCP server: {str(e)}")
        raise HTTPException(status_code=502, detail=f"MySQL MCP server error: {str(e)}")

@router.get("/health")
def mysql_mcp_health_check():
    """Check MySQL MCP server health"""
    try:
        result = _make_mysql_mcp_request("GET", "/health")
        return {
            "mysql_mcp_available": True,
            "mysql_mcp_status": result,
            "message": "MySQL MCP server is running"
        }
    except HTTPException as e:
        return {
            "mysql_mcp_available": False,
            "mysql_mcp_status": None,
            "error": e.detail,
            "message": "MySQL MCP server is not available"
        }

@router.post("/query")
def mysql_mcp_query(
    request: QueryRequest,
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db)
):
    """Execute SELECT query through MySQL MCP"""
    
    # Validate query is not empty
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Security: Only allow SELECT queries
    query_upper = request.query.strip().upper()
    
    # Check for valid query types
    valid_starts = ('SELECT', 'SHOW TABLES', 'SHOW COLUMNS', 'DESCRIBE', 'EXPLAIN')
    if not any(query_upper.startswith(start) for start in valid_starts):
        raise HTTPException(
            status_code=400, 
            detail="Only SELECT, SHOW TABLES, SHOW COLUMNS, DESCRIBE, and EXPLAIN queries are allowed"
        )
    
    # Add domain filtering for non-super-admin users
    if principal.role != "super_admin" and principal.domain_id is not None:
        # Only apply domain filtering for SELECT queries that might need it
        if query_upper.startswith('SELECT'):
            if request.parameters is None:
                request.parameters = {}
            # Only add domain_id if it's not already in the query
            if ':domain_id' not in request.query.lower() and 'domain_id' not in str(request.parameters):
                request.parameters["current_user_domain_id"] = principal.domain_id
    
    try:
        logger.info(f"Executing query: {request.query[:100]}...")
        result = _make_mysql_mcp_request("POST", "/query", {
            "query": request.query,
            "parameters": request.parameters
        })
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query execution error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")

@router.post("/insert")
def mysql_mcp_insert(
    request: InsertRequest,
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db)
):
    """Insert data through MySQL MCP"""
    
    # Add user and domain context
    if "user_id" not in request.data:
        request.data["user_id"] = user.id
    if "domain_id" not in request.data and principal.domain_id is not None:
        request.data["domain_id"] = principal.domain_id
    
    try:
        result = _make_mysql_mcp_request("POST", "/insert", {
            "table": request.table,
            "data": request.data
        })
        return result
    except HTTPException:
        raise

@router.post("/update")
def mysql_mcp_update(
    request: UpdateRequest,
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db)
):
    """Update data through MySQL MCP"""
    
    # Add domain filtering for security
    if principal.role != "super_admin" and principal.domain_id is not None:
        if request.where_parameters is None:
            request.where_parameters = {}
        request.where_parameters["domain_id"] = principal.domain_id
        
        # Ensure WHERE clause includes domain filter
        if "domain_id" not in request.where_clause.lower():
            if "WHERE" in request.where_clause.upper():
                request.where_clause += f" AND domain_id = :domain_id"
            else:
                request.where_clause = f"domain_id = :domain_id AND ({request.where_clause})"
    
    try:
        result = _make_mysql_mcp_request("POST", "/update", {
            "table": request.table,
            "data": request.data,
            "where_clause": request.where_clause,
            "where_parameters": request.where_parameters
        })
        return result
    except HTTPException:
        raise

@router.get("/schema")
def mysql_mcp_schema(
    table_name: Optional[str] = None,
    principal = Depends(get_current_principal)
):
    """Get schema information through MySQL MCP"""
    try:
        if table_name:
            result = _make_mysql_mcp_request("GET", f"/schema/{table_name}")
        else:
            result = _make_mysql_mcp_request("GET", "/schema")
        return result
    except HTTPException:
        raise

@router.get("/domain-analytics")
def get_domain_analytics(
    domain_id: Optional[int] = None,
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db)
):
    """Get comprehensive analytics for a domain through MySQL MCP"""
    
    # Determine domain ID
    if domain_id is None:
        if principal.role == "super_admin":
            raise HTTPException(
                status_code=400, 
                detail="Super admin must specify domain_id parameter"
            )
        else:
            domain_id = user.domain_id
    
    if domain_id is None:
        raise HTTPException(status_code=400, detail="No domain specified")
    
    # Security check: regular users can only access their own domain
    if principal.role != "super_admin" and domain_id != principal.domain_id:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: You can only view analytics for your own domain"
        )
    
    try:
        # Get user statistics
        user_stats = _make_mysql_mcp_request("POST", "/query", {
            "query": """
                SELECT 
                  COUNT(*) as user_count,
                  COUNT(CASE WHEN role_based = 'admin' THEN 1 END) as admin_count,
                  COUNT(CASE WHEN role_based = 'user' THEN 1 END) as regular_user_count
                FROM users 
                WHERE domain_id = :domain_id
            """,
            "parameters": {"domain_id": domain_id}
        })
        
        # Get document statistics
        doc_stats = _make_mysql_mcp_request("POST", "/query", {
            "query": """
                SELECT 
                  COUNT(*) as doc_count,
                  COUNT(DISTINCT user_id) as unique_uploaders
                FROM docs 
                WHERE domain_id = :domain_id AND active = 1
            """,
            "parameters": {"domain_id": domain_id}
        })
        
        # Get chunk statistics
        chunk_stats = _make_mysql_mcp_request("POST", "/query", {
            "query": """
                SELECT 
                  COUNT(*) as chunk_count,
                  AVG(LENGTH(content)) as avg_chunk_length,
                  MAX(LENGTH(content)) as max_chunk_length,
                  MIN(LENGTH(content)) as min_chunk_length
                FROM chunks 
                WHERE domain_id = :domain_id
            """,
            "parameters": {"domain_id": domain_id}
        })
        
        # Get chat statistics
        chat_stats = _make_mysql_mcp_request("POST", "/query", {
            "query": """
                SELECT 
                  COUNT(DISTINCT cs.id) as session_count,
                  COUNT(cm.id) as message_count,
                  COUNT(DISTINCT cs.user_id) as unique_users
                FROM chat_sessions cs
                LEFT JOIN chat_messages cm ON cs.id = cm.session_id
                WHERE cs.domain_id = :domain_id
            """,
            "parameters": {"domain_id": domain_id}
        })
        
        # Get feedback statistics
        feedback_stats = _make_mysql_mcp_request("POST", "/query", {
            "query": """
                SELECT 
                  COUNT(*) as total_feedback,
                  AVG(rating) as avg_rating,
                  COUNT(CASE WHEN rating >= 4 THEN 1 END) as positive_feedback,
                  COUNT(CASE WHEN rating <= 2 THEN 1 END) as negative_feedback
                FROM feedback 
                WHERE domain_id = :domain_id
            """,
            "parameters": {"domain_id": domain_id}
        })
        
        return {
            "success": True,
            "domain_id": domain_id,
            "user_stats": user_stats.get("data", [{}])[0] if user_stats.get("success") else {},
            "document_stats": doc_stats.get("data", [{}])[0] if doc_stats.get("success") else {},
            "chunk_stats": chunk_stats.get("data", [{}])[0] if chunk_stats.get("success") else {},
            "chat_stats": chat_stats.get("data", [{}])[0] if chat_stats.get("success") else {},
            "feedback_stats": feedback_stats.get("data", [{}])[0] if feedback_stats.get("success") else {},
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analytics generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analytics generation failed: {str(e)}")

@router.post("/search-content")
def search_content(
    search_term: str,
    domain_id: Optional[int] = None,
    limit: int = 10,
    principal = Depends(get_current_principal),
    user: User = Depends(get_current_user_db)
):
    """Search content across chunks through MySQL MCP"""
    
    # Determine domain ID
    if domain_id is None:
        if principal.role == "super_admin":
            domain_id = user.domain_id or 1
        else:
            domain_id = user.domain_id
    
    if domain_id is None:
        raise HTTPException(status_code=400, detail="No domain specified")
    
    # Security check
    if principal.role != "super_admin" and domain_id != principal.domain_id:
        raise HTTPException(status_code=403, detail="Access denied to this domain")
    
    try:
        result = _make_mysql_mcp_request("POST", "/query", {
            "query": """
                SELECT 
                  c.id,
                  c.content,
                  c.meta_data,
                  d.name as doc_name,
                  u.username
                FROM chunks c
                JOIN docs d ON c.doc_id = d.id
                JOIN users u ON c.user_id = u.id
                WHERE c.domain_id = :domain_id
                  AND (c.content LIKE :search_term OR c.meta_data LIKE :search_term)
                ORDER BY c.id DESC
                LIMIT :limit
            """,
            "parameters": {
                "domain_id": domain_id,
                "search_term": f"%{search_term}%",
                "limit": limit
            }
        })
        return result
    except HTTPException:
        raise