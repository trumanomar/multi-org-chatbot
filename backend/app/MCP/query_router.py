"""
Query Router for Intelligent MCP Selection
Routes user queries to the appropriate data source: Vector DB, Graph, or MySQL
"""

from typing import List, Dict, Any, Optional
from enum import Enum
import re
from openai import OpenAI

class DataSource(Enum):
    VECTOR = "vector"  # For semantic document search
    GRAPH = "graph"    # For relationship/entity queries
    MYSQL = "mysql"    # For structured data queries
    HYBRID = "hybrid"  # Use multiple sources
    GENERATIVE = "generative"  # Pure AI generation, no retrieval

class QueryRouter:
    """Routes queries to appropriate data sources"""
    
    def __init__(self, openai_client: OpenAI):
        self.client = openai_client
        
        # Keywords that indicate each data source
        self.vector_keywords = [
            'document', 'content', 'chunk', 'text', 'meaning', 'semantic',
            'similar', 'about', 'explain', 'what does', 'summarize'
        ]
        
        self.graph_keywords = [
            'relationship', 'connected', 'related', 'entity', 'how are',
            'connection', 'network', 'link', 'between'
        ]
        
        self.mysql_keywords = [
            'count', 'how many', 'list', 'show me', 'statistics', 'total',
            'users', 'documents', 'sessions', 'feedback', 'average', 'sum',
            'recent', 'last', 'first', 'analytics', 'data', 'database',
            'who uploaded', 'which user', 'most active'
        ]
    
    def route_query(self, query: str, use_llm: bool = True) -> Dict[str, Any]:
        """
        Route a query to the appropriate data source(s)
        
        Args:
            query: User's question
            use_llm: Whether to use LLM for routing (more accurate but slower)
            
        Returns:
            Dictionary with routing decision and reasoning
        """
        query_lower = query.lower()
        
        # First, try rule-based routing (fast)
        rule_based_result = self._rule_based_routing(query_lower)
        
        if not use_llm:
            return rule_based_result
        
        # For complex queries, use LLM routing (more accurate)
        try:
            llm_result = self._llm_based_routing(query)
            # Combine both approaches - LLM takes precedence
            return llm_result
        except Exception as e:
            print(f"LLM routing failed, falling back to rules: {e}")
            return rule_based_result
    
    def _rule_based_routing(self, query_lower: str) -> Dict[str, Any]:
        """Fast rule-based routing using keyword matching"""
        
        vector_score = sum(1 for kw in self.vector_keywords if kw in query_lower)
        graph_score = sum(1 for kw in self.graph_keywords if kw in query_lower)
        mysql_score = sum(1 for kw in self.mysql_keywords if kw in query_lower)
        
        scores = {
            DataSource.VECTOR: vector_score,
            DataSource.GRAPH: graph_score,
            DataSource.MYSQL: mysql_score
        }
        
        max_score = max(scores.values())
        
        # If no clear match, default to hybrid
        if max_score == 0:
            return {
                "primary_source": DataSource.GENERATIVE,
                "secondary_sources": [DataSource.VECTOR],
                "confidence": 0.3,
                "reasoning": "No specific keywords detected, using generative + vector search"
            }
        
        # Get primary source
        primary = max(scores, key=scores.get)
        
        # Get secondary sources (scores > 0 but not primary)
        secondary = [src for src, score in scores.items() 
                    if score > 0 and src != primary]
        
        return {
            "primary_source": primary,
            "secondary_sources": secondary,
            "confidence": min(max_score / 3, 1.0),  # Normalize to 0-1
            "reasoning": f"Rule-based: {primary.value} keywords detected"
        }
    
    def _llm_based_routing(self, query: str) -> Dict[str, Any]:
        """Use LLM to intelligently route the query"""
        
        system_prompt = """You are a query router for a RAG system. Analyze the user's question and decide which data source(s) to use:

1. **VECTOR** - For semantic search in documents (use when user asks about document content, meanings, explanations)
2. **GRAPH** - For relationship queries (use when asking about connections, entities, how things relate)
3. **MYSQL** - For structured data queries (use when asking for counts, statistics, lists, analytics, user data)
4. **HYBRID** - Use multiple sources when query needs different types of data
5. **GENERATIVE** - Pure AI generation without retrieval (for general questions, greetings, opinions)

Examples:
- "How many users do we have?" → MYSQL (structured query)
- "Explain the concept of RAG" → VECTOR (semantic search in documents)
- "How are users and documents related?" → GRAPH (relationship query)
- "Show me user statistics and their uploaded documents" → HYBRID (MYSQL + VECTOR)
- "What do you think about AI?" → GENERATIVE (no retrieval needed)

Respond in JSON format:
{
  "primary_source": "vector|graph|mysql|generative",
  "secondary_sources": ["vector", "graph", "mysql"],  // optional
  "confidence": 0.9,  // 0.0 to 1.0
  "reasoning": "Brief explanation of why"
}"""
        
        try:
            response = self.client.chat.completions.create(
                model="llama3.1:8b-instruct-q4_K_M",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Route this query: {query}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            # Convert strings to enums
            result["primary_source"] = DataSource(result["primary_source"])
            result["secondary_sources"] = [
                DataSource(src) for src in result.get("secondary_sources", [])
            ]
            
            return result
            
        except Exception as e:
            raise Exception(f"LLM routing failed: {str(e)}")


def execute_routed_query(
    query: str,
    routing: Dict[str, Any],
    vector_retriever,
    graph_retriever,
    mysql_client,
    domain_id: int,
    user_id: int
) -> Dict[str, Any]:
    """
    Execute the query based on routing decision
    
    Returns combined results from all selected sources
    """
    results = {
        "query": query,
        "routing": routing,
        "sources_used": [],
        "vector_results": [],
        "graph_results": [],
        "mysql_results": [],
        "combined_context": ""
    }
    
    primary = routing["primary_source"]
    secondary = routing.get("secondary_sources", [])
    all_sources = [primary] + secondary
    
    # Execute queries based on routing
    for source in all_sources:
        try:
            if source == DataSource.VECTOR:
                vector_results = vector_retriever.retrieve(query, k=5)
                results["vector_results"] = vector_results
                results["sources_used"].append("vector")
                
            elif source == DataSource.GRAPH:
                graph_results = graph_retriever.query(query)
                results["graph_results"] = graph_results
                results["sources_used"].append("graph")
                
            elif source == DataSource.MYSQL:
                # Route to appropriate MySQL query based on question
                mysql_results = route_mysql_query(query, mysql_client, domain_id, user_id)
                results["mysql_results"] = mysql_results
                results["sources_used"].append("mysql")
                
        except Exception as e:
            print(f"Error querying {source.value}: {e}")
    
    # Combine contexts
    contexts = []
    
    if results["vector_results"]:
        contexts.append("=== Document Context ===")
        for doc in results["vector_results"][:3]:
            contexts.append(doc.get("content", ""))
    
    if results["graph_results"]:
        contexts.append("\n=== Graph Relationships ===")
        contexts.append(str(results["graph_results"]))
    
    if results["mysql_results"]:
        contexts.append("\n=== Database Information ===")
        contexts.append(format_mysql_results(results["mysql_results"]))
    
    results["combined_context"] = "\n\n".join(contexts)
    
    return results


def route_mysql_query(query: str, mysql_client, domain_id: int, user_id: int) -> Dict[str, Any]:
    """
    Intelligently route to appropriate MySQL query based on question
    """
    query_lower = query.lower()
    
    # User statistics
    if any(word in query_lower for word in ['how many users', 'user count', 'total users']):
        return mysql_client.query(
            "SELECT COUNT(*) as user_count FROM users WHERE domain_id = :domain_id",
            {"domain_id": domain_id}
        )
    
    # Document statistics
    if any(word in query_lower for word in ['how many documents', 'document count', 'total documents']):
        return mysql_client.query(
            "SELECT COUNT(*) as doc_count FROM docs WHERE domain_id = :domain_id AND active = 1",
            {"domain_id": domain_id}
        )
    
    # Recent chat messages
    if any(word in query_lower for word in ['recent chats', 'latest messages', 'chat history']):
        return mysql_client.query("""
            SELECT cm.question, cm.answer, cm.created_at, u.username
            FROM chat_messages cm
            JOIN users u ON cm.user_id = u.id
            JOIN chat_sessions cs ON cm.session_id = cs.id
            WHERE cs.domain_id = :domain_id
            ORDER BY cm.created_at DESC
            LIMIT 10
        """, {"domain_id": domain_id})
    
    # User activity
    if any(word in query_lower for word in ['user activity', 'most active', 'active users']):
        return mysql_client.query("""
            SELECT u.username, COUNT(DISTINCT cs.id) as session_count,
                   COUNT(cm.id) as message_count
            FROM users u
            LEFT JOIN chat_sessions cs ON u.id = cs.user_id
            LEFT JOIN chat_messages cm ON cs.id = cm.session_id
            WHERE u.domain_id = :domain_id
            GROUP BY u.id, u.username
            ORDER BY message_count DESC
            LIMIT 10
        """, {"domain_id": domain_id})
    
    # Domain analytics (comprehensive)
    if any(word in query_lower for word in ['analytics', 'statistics', 'summary', 'overview']):
        return mysql_client.query("""
            SELECT 
                (SELECT COUNT(*) FROM users WHERE domain_id = :domain_id) as total_users,
                (SELECT COUNT(*) FROM docs WHERE domain_id = :domain_id AND active = 1) as total_documents,
                (SELECT COUNT(*) FROM chunks WHERE domain_id = :domain_id) as total_chunks,
                (SELECT COUNT(*) FROM chat_sessions WHERE domain_id = :domain_id) as total_sessions,
                (SELECT COUNT(*) FROM chat_messages cm 
                 JOIN chat_sessions cs ON cm.session_id = cs.id 
                 WHERE cs.domain_id = :domain_id) as total_messages
        """, {"domain_id": domain_id})
    
    # Feedback
    if any(word in query_lower for word in ['feedback', 'rating', 'reviews']):
        return mysql_client.query("""
            SELECT AVG(rating) as avg_rating, COUNT(*) as feedback_count,
                   COUNT(CASE WHEN rating >= 4 THEN 1 END) as positive_count
            FROM feedback
            WHERE domain_id = :domain_id
        """, {"domain_id": domain_id})
    
    # Default: return general stats
    return mysql_client.query(
        "SELECT COUNT(*) as item_count FROM users WHERE domain_id = :domain_id",
        {"domain_id": domain_id}
    )


def format_mysql_results(results: Dict[str, Any]) -> str:
    """Format MySQL results for context"""
    if not results.get("success"):
        return "No database results available"
    
    data = results.get("data", [])
    if not data:
        return "No records found"
    
    # Format as readable text
    formatted = []
    for row in data:
        row_str = ", ".join([f"{k}: {v}" for k, v in row.items()])
        formatted.append(row_str)
    
    return "\n".join(formatted)


# Example usage
if __name__ == "__main__":
    from openai import OpenAI
    
    client = OpenAI()
    router = QueryRouter(client)
    
    # Test queries
    test_queries = [
        "How many users are in the system?",
        "Explain what RAG architecture means",
        "How are documents connected to users?",
        "Show me statistics about our platform",
        "What is the weather like today?"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        routing = router.route_query(query, use_llm=True)
        print(f"Route to: {routing['primary_source'].value}")
        print(f"Reasoning: {routing['reasoning']}")
        print(f"Confidence: {routing['confidence']}")