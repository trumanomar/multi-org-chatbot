"""
MySQL MCP Client
Client for communicating with the MySQL MCP server from other MCPs
"""

import requests
import json
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MySQLMCPClient:
    """Client for MySQL MCP server operations"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:5002"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to MySQL MCP server"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise Exception(f"MySQL MCP request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise Exception(f"Invalid JSON response: {str(e)}")
    
    def health_check(self) -> Dict[str, Any]:
        """Check MySQL MCP server health"""
        return self._make_request("GET", "/health")
    
    def query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute SELECT and JOIN SQL queries
        
        Args:
            query: SQL SELECT query
            parameters: Optional parameters for parameterized queries
            
        Returns:
            Query results with data, columns, and row count
        """
        data = {"query": query}
        if parameters:
            data["parameters"] = parameters
        
        return self._make_request("POST", "/query", data)
    
    def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert new rows into a table
        
        Args:
            table: Table name
            data: Dictionary of column-value pairs
            
        Returns:
            Insert results with affected rows and last insert ID
        """
        request_data = {"table": table, "data": data}
        return self._make_request("POST", "/insert", request_data)
    
    def update(
        self, 
        table: str, 
        data: Dict[str, Any], 
        where_clause: str, 
        where_parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update existing rows in a table
        
        Args:
            table: Table name
            data: Dictionary of column-value pairs to update
            where_clause: WHERE clause for the update
            where_parameters: Optional parameters for the WHERE clause
            
        Returns:
            Update results with affected rows
        """
        request_data = {
            "table": table,
            "data": data,
            "where_clause": where_clause
        }
        if where_parameters:
            request_data["where_parameters"] = where_parameters
        
        return self._make_request("POST", "/update", request_data)
    
    def get_schema(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get schema information
        
        Args:
            table_name: Optional specific table name
            
        Returns:
            Schema information for tables
        """
        if table_name:
            return self._make_request("GET", f"/schema/{table_name}")
        else:
            return self._make_request("GET", "/schema")
    
    def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """
        Get table statistics using MCP tools
        
        Args:
            table_name: Table name to get stats for
            
        Returns:
            Table statistics
        """
        # This would use the MCP tool interface
        # For now, we'll use a direct SQL query
        query = f"SELECT COUNT(*) as row_count FROM {table_name}"
        result = self.query(query)
        
        if result.get("success"):
            row_count = result["data"][0]["row_count"] if result["data"] else 0
            return {
                "status": "success",
                "table_name": table_name,
                "row_count": row_count
            }
        else:
            return result

# Example usage and integration functions
def get_users_by_domain(domain_id: int) -> List[Dict[str, Any]]:
    """Get all users for a specific domain"""
    client = MySQLMCPClient()
    
    query = """
    SELECT u.id, u.username, u.email, u.role_based, u.domain_id, d.name as domain_name
    FROM users u
    JOIN domains d ON u.domain_id = d.id
    WHERE u.domain_id = :domain_id
    """
    
    result = client.query(query, {"domain_id": domain_id})
    
    if result.get("success"):
        return result["data"]
    else:
        logger.error(f"Failed to get users: {result.get('message')}")
        return []

def get_chunks_for_document(doc_id: int) -> List[Dict[str, Any]]:
    """Get all chunks for a specific document"""
    client = MySQLMCPClient()
    
    query = """
    SELECT c.id, c.content, c.meta_data, c.user_id, c.domain_id, c.doc_id,
           d.name as doc_name, u.username
    FROM chunks c
    JOIN docs d ON c.doc_id = d.id
    JOIN users u ON c.user_id = u.id
    WHERE c.doc_id = :doc_id
    ORDER BY c.id
    """
    
    result = client.query(query, {"doc_id": doc_id})
    
    if result.get("success"):
        return result["data"]
    else:
        logger.error(f"Failed to get chunks: {result.get('message')}")
        return []

def get_chat_history_for_user(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent chat history for a user"""
    client = MySQLMCPClient()
    
    query = """
    SELECT cm.id, cm.question, cm.answer, cm.created_at,
           cs.id as session_id, u.username
    FROM chat_messages cm
    JOIN chat_sessions cs ON cm.session_id = cs.id
    JOIN users u ON cm.user_id = u.id
    WHERE cm.user_id = :user_id
    ORDER BY cm.created_at DESC
    LIMIT :limit
    """
    
    result = client.query(query, {"user_id": user_id, "limit": limit})
    
    if result.get("success"):
        return result["data"]
    else:
        logger.error(f"Failed to get chat history: {result.get('message')}")
        return []

def get_domain_statistics(domain_id: int) -> Dict[str, Any]:
    """Get comprehensive statistics for a domain"""
    client = MySQLMCPClient()
    
    queries = {
        "users": "SELECT COUNT(*) as count FROM users WHERE domain_id = :domain_id",
        "docs": "SELECT COUNT(*) as count FROM docs WHERE domain_id = :domain_id",
        "chunks": "SELECT COUNT(*) as count FROM chunks WHERE domain_id = :domain_id",
        "chat_sessions": "SELECT COUNT(*) as count FROM chat_sessions WHERE domain_id = :domain_id",
        "chat_messages": """
            SELECT COUNT(*) as count 
            FROM chat_messages cm
            JOIN chat_sessions cs ON cm.session_id = cs.id
            WHERE cs.domain_id = :domain_id
        """
    }
    
    stats = {}
    for stat_name, query in queries.items():
        result = client.query(query, {"domain_id": domain_id})
        if result.get("success") and result["data"]:
            stats[stat_name] = result["data"][0]["count"]
        else:
            stats[stat_name] = 0
    
    return stats

def insert_feedback(user_id: int, domain_id: int, content: str, rating: int, question: str) -> Dict[str, Any]:
    """Insert new feedback record"""
    client = MySQLMCPClient()
    
    data = {
        "user_id": user_id,
        "domain_id": domain_id,
        "content": content,
        "rating": rating,
        "question": question
    }
    
    return client.insert("feedback", data)

def update_user_role(user_id: int, new_role: str) -> Dict[str, Any]:
    """Update user role"""
    client = MySQLMCPClient()
    
    data = {"role_based": new_role}
    where_clause = "id = :user_id"
    where_parameters = {"user_id": user_id}
    
    return client.update("users", data, where_clause, where_parameters)

# Integration with other MCPs
class DoclingMySQLIntegration:
    """Integration between Docling MCP and MySQL MCP"""
    
    def __init__(self):
        self.mysql_client = MySQLMCPClient()
    
    def store_processed_chunks(self, doc_id: int, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store processed chunks from Docling into MySQL"""
        try:
            # Get document info
            doc_result = self.mysql_client.query(
                "SELECT user_id, domain_id FROM docs WHERE id = :doc_id",
                {"doc_id": doc_id}
            )
            
            if not doc_result.get("success") or not doc_result["data"]:
                return {"status": "error", "message": "Document not found"}
            
            doc_info = doc_result["data"][0]
            user_id = doc_info["user_id"]
            domain_id = doc_info["domain_id"]
            
            # Insert chunks
            inserted_count = 0
            for chunk_data in chunks:
                chunk_record = {
                    "content": chunk_data.get("content", ""),
                    "meta_data": json.dumps(chunk_data.get("metadata", {})),
                    "user_id": user_id,
                    "domain_id": domain_id,
                    "doc_id": doc_id
                }
                
                result = self.mysql_client.insert("chunks", chunk_record)
                if result.get("success"):
                    inserted_count += 1
            
            return {
                "status": "success",
                "inserted_chunks": inserted_count,
                "total_chunks": len(chunks)
            }
            
        except Exception as e:
            logger.error(f"Error storing chunks: {e}")
            return {"status": "error", "message": str(e)}

class GraphMySQLIntegration:
    """Integration between Graph MCP and MySQL MCP"""
    
    def __init__(self):
        self.mysql_client = MySQLMCPClient()
    
    def get_chunks_for_graph_building(self, domain_id: int, doc_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get chunks from MySQL for graph building"""
        query = """
        SELECT c.id, c.content, c.meta_data, c.user_id, c.domain_id, c.doc_id,
               d.name as doc_name, u.username
        FROM chunks c
        JOIN docs d ON c.doc_id = d.id
        JOIN users u ON c.user_id = u.id
        WHERE c.domain_id = :domain_id
        """
        
        parameters = {"domain_id": domain_id}
        
        if doc_id:
            query += " AND c.doc_id = :doc_id"
            parameters["doc_id"] = doc_id
        
        query += " ORDER BY c.id"
        
        result = self.mysql_client.query(query, parameters)
        
        if result.get("success"):
            return result["data"]
        else:
            logger.error(f"Failed to get chunks for graph: {result.get('message')}")
            return []
    
    def store_graph_results(self, message_id: int, graph_results: Dict[str, Any]) -> Dict[str, Any]:
        """Store graph query results in chat message"""
        data = {"graph_results": json.dumps(graph_results)}
        where_clause = "id = :message_id"
        where_parameters = {"message_id": message_id}
        
        return self.mysql_client.update("chat_messages", data, where_clause, where_parameters)

if __name__ == "__main__":
    # Test the MySQL MCP client
    client = MySQLMCPClient()
    
    try:
        # Health check
        health = client.health_check()
        print("Health check:", health)
        
        # Get schema
        schema = client.get_schema()
        print("Schema:", schema)
        
        # Test query
        users = client.query("SELECT COUNT(*) as user_count FROM users")
        print("User count:", users)
        
    except Exception as e:
        print(f"Test failed: {e}")
