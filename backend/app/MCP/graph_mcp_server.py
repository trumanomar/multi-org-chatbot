"""
Graph MCP Server
Model Context Protocol server for graph database operations
Separate from docling MCP server for dedicated graph functionality
"""

from fastapi import FastAPI, HTTPException
from fastmcp import FastMCP
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import json
import os
import logging
from app.GraphDB.graph_integration import GraphRAGIntegration
from app.GraphDB.config import get_graph_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app for HTTP endpoints
fastapi_app = FastAPI(
    title="Graph MCP API Server",
    description="Graph database operations API",
    version="1.0.0"
)

# Pydantic models for request/response
class GraphBuildRequest(BaseModel):
    domain_id: int
    doc_id: Optional[int] = None
    user_id: Optional[int] = None

class GraphQueryRequest(BaseModel):
    query: str
    domain_id: int
    max_results: int = 10

class GraphUpdateRequest(BaseModel):
    domain_id: int
    doc_id: int
    user_id: int

class GraphStatsResponse(BaseModel):
    total_nodes: int
    total_edges: int
    node_types: Dict[str, int]
    edge_types: Dict[str, int]
    connected_components: int

# Global graph integration instance
graph_integration = None

def get_graph_integration():
    """Get or create graph integration instance"""
    global graph_integration
    if graph_integration is None:
        config = get_graph_config()
        graph_integration = GraphRAGIntegration(
            ollama_url=config["base_url"],
            model=config["model"],
            output_dir=config["output_dir"]
        )
    return graph_integration

# HTTP Endpoints
@fastapi_app.post("/build_graph")
async def build_graph_endpoint(req: GraphBuildRequest):
    """Build graph from chunks for a domain"""
    try:
        graph = get_graph_integration()
        result = await graph.build_graph_from_chunks(
            domain_id=req.domain_id,
            doc_id=req.doc_id,
            user_id=req.user_id
        )
        return result
    except Exception as e:
        logger.error(f"Error building graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.post("/query_graph")
async def query_graph_endpoint(req: GraphQueryRequest):
    """Query the graph for relevant information"""
    try:
        graph = get_graph_integration()
        result = await graph.query_graph(
            query=req.query,
            domain_id=req.domain_id,
            max_results=req.max_results
        )
        return result
    except Exception as e:
        logger.error(f"Error querying graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.post("/update_graph")
async def update_graph_endpoint(req: GraphUpdateRequest):
    """Update graph with new chunks"""
    try:
        graph = get_graph_integration()
        result = await graph.update_graph_with_new_chunks(
            domain_id=req.domain_id,
            doc_id=req.doc_id,
            user_id=req.user_id
        )
        return result
    except Exception as e:
        logger.error(f"Error updating graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.get("/graph_stats/{domain_id}")
async def get_graph_stats(domain_id: int):
    """Get graph statistics"""
    try:
        graph = get_graph_integration()
        stats = graph.get_graph_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting graph stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.post("/load_graph/{domain_id}")
async def load_existing_graph(domain_id: int):
    """Load existing graph from file"""
    try:
        graph = get_graph_integration()
        success = await graph.load_existing_graph(domain_id)
        return {"success": success, "domain_id": domain_id}
    except Exception as e:
        logger.error(f"Error loading graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "graph-mcp"}

# MCP Server Creation
def create_graph_mcp_server():
    """Create MCP server for graph operations"""
    mcp_app = FastAPI()
    mcp = FastMCP.from_fastapi(mcp_app, name="graph-mcp")
    
    @mcp.tool()
    async def build_graph_tool(domain_id: int, doc_id: Optional[int] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Build a graph from chunks for a specific domain
        
        Args:
            domain_id: The domain ID to build graph for
            doc_id: Optional document ID to filter chunks
            user_id: Optional user ID to filter chunks
            
        Returns:
            Dictionary with build results and statistics
        """
        try:
            graph = get_graph_integration()
            result = await graph.build_graph_from_chunks(
                domain_id=domain_id,
                doc_id=doc_id,
                user_id=user_id
            )
            return result
        except Exception as e:
            logger.error(f"Error in build_graph_tool: {e}")
            return {"status": "error", "message": str(e)}
    
    @mcp.tool()
    async def query_graph_tool(query: str, domain_id: int, max_results: int = 10) -> Dict[str, Any]:
        """
        Query the graph for relevant information
        
        Args:
            query: The search query
            domain_id: Domain ID to search in
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary with query results
        """
        try:
            graph = get_graph_integration()
            result = await graph.query_graph(
                query=query,
                domain_id=domain_id,
                max_results=max_results
            )
            return result
        except Exception as e:
            logger.error(f"Error in query_graph_tool: {e}")
            return {"status": "error", "message": str(e)}
    
    @mcp.tool()
    async def update_graph_tool(domain_id: int, doc_id: int, user_id: int) -> Dict[str, Any]:
        """
        Update graph with new chunks from a document
        
        Args:
            domain_id: Domain ID
            doc_id: Document ID to add chunks from
            user_id: User ID
            
        Returns:
            Dictionary with update results
        """
        try:
            graph = get_graph_integration()
            result = await graph.update_graph_with_new_chunks(
                domain_id=domain_id,
                doc_id=doc_id,
                user_id=user_id
            )
            return result
        except Exception as e:
            logger.error(f"Error in update_graph_tool: {e}")
            return {"status": "error", "message": str(e)}
    
    @mcp.tool()
    async def get_graph_stats_tool(domain_id: int) -> Dict[str, Any]:
        """
        Get statistics about the graph
        
        Args:
            domain_id: Domain ID to get stats for
            
        Returns:
            Dictionary with graph statistics
        """
        try:
            graph = get_graph_integration()
            stats = graph.get_graph_statistics()
            return {
                "status": "success",
                "domain_id": domain_id,
                "stats": stats
            }
        except Exception as e:
            logger.error(f"Error in get_graph_stats_tool: {e}")
            return {"status": "error", "message": str(e)}
    
    @mcp.tool()
    async def load_graph_tool(domain_id: int) -> Dict[str, Any]:
        """
        Load existing graph from file
        
        Args:
            domain_id: Domain ID to load graph for
            
        Returns:
            Dictionary with load results
        """
        try:
            graph = get_graph_integration()
            success = await graph.load_existing_graph(domain_id)
            return {
                "status": "success" if success else "not_found",
                "domain_id": domain_id,
                "loaded": success
            }
        except Exception as e:
            logger.error(f"Error in load_graph_tool: {e}")
            return {"status": "error", "message": str(e)}
    
    @mcp.tool()
    async def search_connected_chunks_tool(chunk_id: int, domain_id: int, max_depth: int = 2) -> Dict[str, Any]:
        """
        Find chunks connected to a specific chunk in the graph
        
        Args:
            chunk_id: The chunk ID to find connections for
            domain_id: Domain ID
            max_depth: Maximum depth to search (default: 2)
            
        Returns:
            Dictionary with connected chunks
        """
        try:
            graph = get_graph_integration()
            
            # Check if graph has nodes
            if graph.graph.number_of_nodes() == 0:
                return {
                    "status": "success",
                    "message": "Graph is empty",
                    "connected_chunks": []
                }
            
            # Find the node for this chunk
            node_id = f"chunk_{chunk_id}"
            if node_id not in graph.graph.nodes:
                return {
                    "status": "success",
                    "message": f"Chunk {chunk_id} not found in graph",
                    "connected_chunks": []
                }
            
            # Find connected nodes using BFS
            connected_nodes = []
            visited = set()
            queue = [(node_id, 0)]  # (node, depth)
            
            while queue:
                current_node, depth = queue.pop(0)
                
                if depth > max_depth or current_node in visited:
                    continue
                    
                visited.add(current_node)
                
                # Get neighbors
                neighbors = list(graph.graph.neighbors(current_node))
                for neighbor in neighbors:
                    if neighbor not in visited:
                        neighbor_data = graph.graph.nodes[neighbor]
                        if neighbor_data.get("domain_id") == domain_id:
                            connected_nodes.append({
                                "chunk_id": neighbor_data.get("chunk_id"),
                                "content": neighbor_data.get("content", "")[:200] + "...",
                                "doc_name": neighbor_data.get("doc_name"),
                                "depth": depth + 1
                            })
                            queue.append((neighbor, depth + 1))
            
            return {
                "status": "success",
                "chunk_id": chunk_id,
                "connected_chunks": connected_nodes,
                "total_connected": len(connected_nodes)
            }
            
        except Exception as e:
            logger.error(f"Error in search_connected_chunks_tool: {e}")
            return {"status": "error", "message": str(e)}
    
    @mcp.tool()
    async def get_graph_path_tool(source_chunk_id: int, target_chunk_id: int, domain_id: int) -> Dict[str, Any]:
        """
        Find the shortest path between two chunks in the graph
        
        Args:
            source_chunk_id: Source chunk ID
            target_chunk_id: Target chunk ID
            domain_id: Domain ID
            
        Returns:
            Dictionary with path information
        """
        try:
            graph = get_graph_integration()
            
            # Check if graph has nodes
            if graph.graph.number_of_nodes() == 0:
                return {
                    "status": "success",
                    "message": "Graph is empty",
                    "path": [],
                    "path_length": 0
                }
            
            source_node = f"chunk_{source_chunk_id}"
            target_node = f"chunk_{target_chunk_id}"
            
            if source_node not in graph.graph.nodes:
                return {
                    "status": "error",
                    "message": f"Source chunk {source_chunk_id} not found in graph"
                }
            
            if target_node not in graph.graph.nodes:
                return {
                    "status": "error",
                    "message": f"Target chunk {target_chunk_id} not found in graph"
                }
            
            # Find shortest path
            try:
                path = graph.graph.shortest_path(source_node, target_node)
                path_data = []
                
                for node_id in path:
                    node_data = graph.graph.nodes[node_id]
                    path_data.append({
                        "chunk_id": node_data.get("chunk_id"),
                        "content": node_data.get("content", "")[:100] + "...",
                        "doc_name": node_data.get("doc_name")
                    })
                
                return {
                    "status": "success",
                    "path": path_data,
                    "path_length": len(path) - 1,
                    "source_chunk": source_chunk_id,
                    "target_chunk": target_chunk_id
                }
                
            except Exception:
                return {
                    "status": "success",
                    "message": "No path found between chunks",
                    "path": [],
                    "path_length": -1
                }
            
        except Exception as e:
            logger.error(f"Error in get_graph_path_tool: {e}")
            return {"status": "error", "message": str(e)}
    
    return mcp_app

# Run both servers
if __name__ == "__main__":
    import uvicorn
    
    # Run FastAPI server for HTTP endpoints
    uvicorn.run(fastapi_app, host="127.0.0.1", port=5001)
