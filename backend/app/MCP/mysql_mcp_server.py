"""
MySQL MCP Server
Model Context Protocol server for MySQL database operations
Provides REST endpoints for SQL query, insert, update, and schema operations
"""

from fastapi import FastAPI, HTTPException, Depends
from fastmcp import FastMCP
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import asyncio
import json
import logging
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from app.DB.db import engine, get_db, DATABASE_URL
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app for HTTP endpoints
fastapi_app = FastAPI(
    title="MySQL MCP API Server",
    description="MySQL database operations API for RAG system integration",
    version="1.0.0"
)

# Pydantic models for request/response
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

class SchemaRequest(BaseModel):
    table_name: Optional[str] = None

class QueryResponse(BaseModel):
    success: bool
    data: List[Dict[str, Any]]
    columns: List[str]
    row_count: int
    message: Optional[str] = None

class InsertResponse(BaseModel):
    success: bool
    last_insert_id: Optional[int] = None
    affected_rows: int
    message: Optional[str] = None

class UpdateResponse(BaseModel):
    success: bool
    affected_rows: int
    message: Optional[str] = None

class SchemaResponse(BaseModel):
    success: bool
    tables: List[Dict[str, Any]]
    message: Optional[str] = None

class TableSchemaResponse(BaseModel):
    success: bool
    table_name: str
    columns: List[Dict[str, Any]]
    indexes: List[Dict[str, Any]]
    foreign_keys: List[Dict[str, Any]]
    message: Optional[str] = None

# Global database connection
db_engine = None

def get_database_engine():
    """Get or create database engine"""
    global db_engine
    if db_engine is None:
        db_engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
    return db_engine

def execute_sql_query(query: str, parameters: Optional[Dict[str, Any]] = None) -> tuple:
    """Execute SQL query and return results"""
    try:
        engine = get_database_engine()
        
        # Validate query is not empty or incomplete
        query_stripped = query.strip()
        if not query_stripped:
            raise ValueError("Query cannot be empty")
        
        # Log the query for debugging
        logger.info(f"Executing query: {query_stripped[:200]}...")
        if parameters:
            logger.info(f"With parameters: {parameters}")
        
        with engine.connect() as connection:
            # Execute the query
            if parameters:
                result = connection.execute(text(query_stripped), parameters)
            else:
                result = connection.execute(text(query_stripped))
            
            # Get column names
            columns = list(result.keys()) if result.rowcount >= 0 else []
            
            # Fetch all rows
            rows = result.fetchall()
            
            # Convert rows to dictionaries
            data = []
            for row in rows:
                row_dict = {}
                for i, value in enumerate(row):
                    column_name = columns[i] if i < len(columns) else f"column_{i}"
                    # Convert non-serializable types
                    if hasattr(value, 'isoformat'):  # datetime objects
                        row_dict[column_name] = value.isoformat()
                    else:
                        row_dict[column_name] = value
                data.append(row_dict)
            
            logger.info(f"Query returned {len(data)} rows")
            return data, columns, len(data)
            
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy error: {e}")
        raise HTTPException(status_code=400, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

def execute_sql_modification(query: str, parameters: Optional[Dict[str, Any]] = None) -> tuple:
    """Execute SQL modification (INSERT, UPDATE, DELETE) and return affected rows and last insert ID"""
    try:
        engine = get_database_engine()
        
        # Validate query is not empty
        query_stripped = query.strip()
        if not query_stripped:
            raise ValueError("Query cannot be empty")
        
        logger.info(f"Executing modification: {query_stripped[:200]}...")
        if parameters:
            logger.info(f"With parameters: {parameters}")
        
        with engine.connect() as connection:
            # Begin transaction
            trans = connection.begin()
            
            try:
                # Execute the query
                if parameters:
                    result = connection.execute(text(query_stripped), parameters)
                else:
                    result = connection.execute(text(query_stripped))
                
                # Commit transaction
                trans.commit()
                
                # Get last insert ID if available
                last_insert_id = None
                if hasattr(result, 'lastrowid'):
                    last_insert_id = result.lastrowid
                
                logger.info(f"Modification affected {result.rowcount} rows")
                return result.rowcount, last_insert_id
                
            except Exception as e:
                trans.rollback()
                raise e
                
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy error: {e}")
        raise HTTPException(status_code=400, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# HTTP Endpoints
@fastapi_app.post("/query", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest):
    """
    Execute SELECT and JOIN SQL queries
    
    Supports parameterized queries for security.
    Example: {"query": "SELECT * FROM users WHERE domain_id = :domain_id", "parameters": {"domain_id": 1}}
    """
    try:
        # Validate query is not empty
        if not req.query or not req.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Basic security check - only allow SELECT statements
        query_upper = req.query.strip().upper()
        
        # Allow common read-only queries
        allowed_starts = ('SELECT', 'SHOW TABLES', 'SHOW COLUMNS', 'DESCRIBE', 'EXPLAIN')
        if not any(query_upper.startswith(start) for start in allowed_starts):
            raise HTTPException(
                status_code=400, 
                detail="Only SELECT, SHOW TABLES, SHOW COLUMNS, DESCRIBE, and EXPLAIN queries are allowed"
            )
        
        data, columns, row_count = execute_sql_query(req.query, req.parameters)
        
        return QueryResponse(
            success=True,
            data=data,
            columns=columns,
            row_count=row_count,
            message=f"Query executed successfully, returned {row_count} rows"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in query endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.post("/insert", response_model=InsertResponse)
async def insert_endpoint(req: InsertRequest):
    """
    Insert new rows into a table
    
    Example: {"table": "users", "data": {"username": "john", "email": "john@example.com", "domain_id": 1}}
    """
    try:
        if not req.data:
            raise HTTPException(status_code=400, detail="Data cannot be empty")
        
        # Build INSERT query
        columns = list(req.data.keys())
        placeholders = [f":{col}" for col in columns]
        
        query = f"INSERT INTO {req.table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        
        affected_rows, last_insert_id = execute_sql_modification(query, req.data)
        
        return InsertResponse(
            success=True,
            last_insert_id=last_insert_id,
            affected_rows=affected_rows,
            message=f"Successfully inserted {affected_rows} row(s)"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in insert endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.post("/update", response_model=UpdateResponse)
async def update_endpoint(req: UpdateRequest):
    """
    Modify existing rows in a table
    
    Example: {"table": "users", "data": {"username": "new_name"}, "where_clause": "id = :id", "where_parameters": {"id": 1}}
    """
    try:
        if not req.data:
            raise HTTPException(status_code=400, detail="Data cannot be empty")
        
        if not req.where_clause:
            raise HTTPException(status_code=400, detail="WHERE clause is required for safety")
        
        # Build UPDATE query
        set_clauses = [f"{col} = :{col}" for col in req.data.keys()]
        query = f"UPDATE {req.table} SET {', '.join(set_clauses)} WHERE {req.where_clause}"
        
        # Merge data and where_parameters
        parameters = req.data.copy()
        if req.where_parameters:
            parameters.update(req.where_parameters)
        
        affected_rows, _ = execute_sql_modification(query, parameters)
        
        return UpdateResponse(
            success=True,
            affected_rows=affected_rows,
            message=f"Successfully updated {affected_rows} row(s)"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.get("/schema", response_model=SchemaResponse)
async def get_schema():
    """
    List all available tables and basic information
    """
    try:
        engine = get_database_engine()
        inspector = inspect(engine)
        
        tables = []
        table_names = inspector.get_table_names()
        
        for table_name in table_names:
            # Get basic table info
            columns = inspector.get_columns(table_name)
            indexes = inspector.get_indexes(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)
            
            table_info = {
                "table_name": table_name,
                "column_count": len(columns),
                "index_count": len(indexes),
                "foreign_key_count": len(foreign_keys),
                "columns": [
                    {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col["nullable"],
                        "primary_key": col.get("primary_key", False),
                        "default": str(col["default"]) if col["default"] is not None else None
                    }
                    for col in columns
                ],
                "indexes": [
                    {
                        "name": idx["name"],
                        "unique": idx["unique"],
                        "columns": idx["column_names"]
                    }
                    for idx in indexes
                ],
                "foreign_keys": [
                    {
                        "name": fk["name"],
                        "constrained_columns": fk["constrained_columns"],
                        "referred_table": fk["referred_table"],
                        "referred_columns": fk["referred_columns"]
                    }
                    for fk in foreign_keys
                ]
            }
            tables.append(table_info)
        
        return SchemaResponse(
            success=True,
            tables=tables,
            message=f"Retrieved schema for {len(tables)} tables"
        )
        
    except Exception as e:
        logger.error(f"Error in schema endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.get("/schema/{table_name}", response_model=TableSchemaResponse)
async def get_table_schema(table_name: str):
    """
    Get detailed schema information for a specific table
    """
    try:
        engine = get_database_engine()
        inspector = inspect(engine)
        
        # Check if table exists
        if table_name not in inspector.get_table_names():
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        # Get detailed table info
        columns = inspector.get_columns(table_name)
        indexes = inspector.get_indexes(table_name)
        foreign_keys = inspector.get_foreign_keys(table_name)
        
        return TableSchemaResponse(
            success=True,
            table_name=table_name,
            columns=[
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col["nullable"],
                    "primary_key": col.get("primary_key", False),
                    "default": str(col["default"]) if col["default"] is not None else None,
                    "autoincrement": col.get("autoincrement", False)
                }
                for col in columns
            ],
            indexes=[
                {
                    "name": idx["name"],
                    "unique": idx["unique"],
                    "columns": idx["column_names"]
                }
                for idx in indexes
            ],
            foreign_keys=[
                {
                    "name": fk["name"],
                    "constrained_columns": fk["constrained_columns"],
                    "referred_table": fk["referred_table"],
                    "referred_columns": fk["referred_columns"]
                }
                for fk in foreign_keys
            ],
            message=f"Retrieved detailed schema for table '{table_name}'"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in table schema endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.get("/health")
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        engine = get_database_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        
        return {
            "status": "healthy", 
            "service": "mysql-mcp",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database connection failed")

# Run server
if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting MySQL MCP Server on port 5002...")
    # Run FastAPI server for HTTP endpoints
    uvicorn.run(fastapi_app, host="127.0.0.1", port=5002)