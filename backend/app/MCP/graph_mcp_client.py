"""
Graph MCP Client
Client for connecting to the Graph MCP server from the chatbot
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class GraphMCPClient:
    """Client for Graph MCP server operations"""
    
    def __init__(self, mcp_url: str = "http://127.0.0.1:5001"):
        """
        Initialize Graph MCP Client
        
        Args:
            mcp_url: URL of the Graph MCP server
        """
        self.mcp_url = mcp_url
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make HTTP request to MCP server
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data
            
        Returns:
            Response data
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.mcp_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                async with self.session.get(url, timeout=30) as response:
                    return await response.json()
            elif method.upper() == "POST":
                async with self.session.post(url, json=data, timeout=30) as response:
                    return await response.json()
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed: {e}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Request error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if MCP server is healthy"""
        return await self._make_request("GET", "/health")
    
    async def build_graph(self, domain_id: int, doc_id: Optional[int] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Build graph from chunks
        
        Args:
            domain_id: Domain ID
            doc_id: Optional document ID
            user_id: Optional user ID
            
        Returns:
            Build results
        """
        data = {
            "domain_id": domain_id,
            "doc_id": doc_id,
            "user_id": user_id
        }
        return await self._make_request("POST", "/build_graph", data)
    
    async def query_graph(self, query: str, domain_id: int, max_results: int = 10) -> Dict[str, Any]:
        """
        Query the graph
        
        Args:
            query: Search query
            domain_id: Domain ID
            max_results: Maximum results
            
        Returns:
            Query results
        """
        data = {
            "query": query,
            "domain_id": domain_id,
            "max_results": max_results
        }
        return await self._make_request("POST", "/query_graph", data)
    
    async def update_graph(self, domain_id: int, doc_id: int, user_id: int) -> Dict[str, Any]:
        """
        Update graph with new chunks
        
        Args:
            domain_id: Domain ID
            doc_id: Document ID
            user_id: User ID
            
        Returns:
            Update results
        """
        data = {
            "domain_id": domain_id,
            "doc_id": doc_id,
            "user_id": user_id
        }
        return await self._make_request("POST", "/update_graph", data)
    
    async def get_graph_stats(self, domain_id: int) -> Dict[str, Any]:
        """
        Get graph statistics
        
        Args:
            domain_id: Domain ID
            
        Returns:
            Graph statistics
        """
        return await self._make_request("GET", f"/graph_stats/{domain_id}")
    
    async def load_graph(self, domain_id: int) -> Dict[str, Any]:
        """
        Load existing graph
        
        Args:
            domain_id: Domain ID
            
        Returns:
            Load results
        """
        return await self._make_request("POST", f"/load_graph/{domain_id}")
    
    async def draw_graph(
        self, 
        domain_id: int, 
        layout: str = "spring", 
        node_size: int = 300, 
        font_size: int = 6,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Draw and save graph visualization
        
        Args:
            domain_id: Domain ID to visualize
            layout: Layout algorithm (spring, kamada_kawai, circular)
            node_size: Size of nodes in visualization
            font_size: Font size for labels
            file_path: Optional custom file path for output
            
        Returns:
            Dictionary with visualization results including file path
        """
        data = {
            "domain_id": domain_id,
            "layout": layout,
            "node_size": node_size,
            "font_size": font_size,
            "file_path": file_path
        }
        return await self._make_request("POST", "/draw_graph", data)
    
    async def search_connected_chunks(self, chunk_id: int, domain_id: int, max_depth: int = 2) -> Dict[str, Any]:
        """
        Find connected chunks
        
        Args:
            chunk_id: Chunk ID
            domain_id: Domain ID
            max_depth: Maximum depth
            
        Returns:
            Connected chunks
        """
        # This would need to be implemented as a new endpoint in the MCP server
        # For now, we'll use the query functionality
        query = f"chunk_id:{chunk_id}"
        return await self.query_graph(query, domain_id, max_results=10)
    
    async def get_graph_path(self, source_chunk_id: int, target_chunk_id: int, domain_id: int) -> Dict[str, Any]:
        """
        Find path between chunks
        
        Args:
            source_chunk_id: Source chunk ID
            target_chunk_id: Target chunk ID
            domain_id: Domain ID
            
        Returns:
            Path information
        """
        # This would need to be implemented as a new endpoint in the MCP server
        # For now, return a placeholder
        return {
            "status": "not_implemented",
            "message": "Graph path finding not yet implemented in HTTP API"
        }
    
    async def query_and_visualize(
        self, 
        query: str, 
        domain_id: int, 
        max_results: int = 10,
        draw_graph: bool = True,
        layout: str = "spring"
    ) -> Dict[str, Any]:
        """
        Convenience method to query graph and optionally create visualization
        
        Args:
            query: Search query
            domain_id: Domain ID
            max_results: Maximum results
            draw_graph: Whether to generate graph visualization
            layout: Layout algorithm for visualization
            
        Returns:
            Combined query results and visualization info
        """
        # Query the graph
        query_results = await self.query_graph(query, domain_id, max_results)
        
        result = {
            "query_results": query_results,
            "visualization": None
        }
        
        # Optionally create visualization
        if draw_graph:
            viz_result = await self.draw_graph(
                domain_id=domain_id,
                layout=layout
            )
            result["visualization"] = viz_result
        
        return result

# Convenience functions for easy integration
async def query_domain_graph(query: str, domain_id: int, mcp_url: str = "http://127.0.0.1:5001") -> Dict[str, Any]:
    """
    Convenience function to query domain graph
    
    Args:
        query: Search query
        domain_id: Domain ID
        mcp_url: MCP server URL
        
    Returns:
        Query results
    """
    async with GraphMCPClient(mcp_url) as client:
        return await client.query_graph(query, domain_id)

async def build_domain_graph(domain_id: int, mcp_url: str = "http://127.0.0.1:5001") -> Dict[str, Any]:
    """
    Convenience function to build domain graph
    
    Args:
        domain_id: Domain ID
        mcp_url: MCP server URL
        
    Returns:
        Build results
    """
    async with GraphMCPClient(mcp_url) as client:
        return await client.build_graph(domain_id)

async def get_domain_graph_stats(domain_id: int, mcp_url: str = "http://127.0.0.1:5001") -> Dict[str, Any]:
    """
    Convenience function to get domain graph stats
    
    Args:
        domain_id: Domain ID
        mcp_url: MCP server URL
        
    Returns:
        Graph statistics
    """
    async with GraphMCPClient(mcp_url) as client:
        return await client.get_graph_stats(domain_id)

async def draw_domain_graph(
    domain_id: int, 
    layout: str = "spring",
    mcp_url: str = "http://127.0.0.1:5001"
) -> Dict[str, Any]:
    """
    Convenience function to draw domain graph
    
    Args:
        domain_id: Domain ID
        layout: Layout algorithm
        mcp_url: MCP server URL
        
    Returns:
        Visualization results with file path
    """
    async with GraphMCPClient(mcp_url) as client:
        return await client.draw_graph(domain_id, layout=layout)

async def query_and_visualize_graph(
    query: str,
    domain_id: int,
    layout: str = "spring",
    mcp_url: str = "http://127.0.0.1:5001"
) -> Dict[str, Any]:
    """
    Convenience function to query and visualize graph in one call
    
    Args:
        query: Search query
        domain_id: Domain ID
        layout: Layout algorithm
        mcp_url: MCP server URL
        
    Returns:
        Combined query and visualization results
    """
    async with GraphMCPClient(mcp_url) as client:
        return await client.query_and_visualize(
            query=query,
            domain_id=domain_id,
            draw_graph=True,
            layout=layout
        )

# Example usage
async def example_usage():
    """Example of how to use the Graph MCP Client"""
    print("🔗 Graph MCP Client Example")
    
    async with GraphMCPClient() as client:
        # Health check
        health = await client.health_check()
        print(f"Health: {health}")
        
        # Get graph stats
        stats = await client.get_graph_stats(1)
        print(f"Stats: {stats}")
        
        # Query graph and visualize
        results = await client.query_and_visualize(
            query="machine learning",
            domain_id=1,
            draw_graph=True,
            layout="spring"
        )
        print(f"Query results: {results['query_results']}")
        print(f"Visualization: {results['visualization']}")
        
        # Or just draw the graph
        viz = await client.draw_graph(
            domain_id=1,
            layout="kamada_kawai",
            node_size=500,
            font_size=8
        )
        print(f"Graph visualization saved to: {viz.get('path')}")

if __name__ == "__main__":
    asyncio.run(example_usage())