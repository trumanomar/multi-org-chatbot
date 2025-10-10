# app/Routes/GraphRoute.py
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import os
import asyncio
import logging

from app.DB.db import get_db
from app.auth.dependencies import get_current_principal, Principal
from app.GraphDB.graph_integration import GraphRAGIntegration
from pydantic import BaseModel

router = APIRouter(prefix="/graph", tags=["Graph"])
logger = logging.getLogger(__name__)

# Request/Response models
class GraphQueryRequest(BaseModel):
    query: str
    max_results: Optional[int] = 10

class GraphQueryResponse(BaseModel):
    status: str
    query: str
    results: list
    total_found: int
    domain_id: int
    graph_stats: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

# Initialize graph integration instance (reuse across requests)
_graph_instances = {}

def get_graph_integration(domain_id: int) -> GraphRAGIntegration:
    """Get or create graph integration instance for domain"""
    if domain_id not in _graph_instances:
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b-instruct-q4_K_M")
        
        _graph_instances[domain_id] = GraphRAGIntegration(
            ollama_url=ollama_url,
            model=ollama_model,
            output_dir="./graph_output"
        )
        
        # Try to load existing graph
        asyncio.create_task(
            _graph_instances[domain_id].load_existing_graph(domain_id)
        )
    
    return _graph_instances[domain_id]

@router.get("/query/{domain_id}", response_model=GraphQueryResponse)
async def query_graph(
    domain_id: int,
    query: str = Query(..., description="Search query for the graph"),
    max_results: int = Query(10, description="Maximum number of results to return"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal)
):
    """
    Query the knowledge graph for a specific domain
    
    Args:
        domain_id: Domain ID to query
        query: Search query string
        max_results: Maximum number of results
    
    Returns:
        Query results with graph relationships
    """
    
    try:
        # Validate domain access (optional - based on your auth logic)
        if principal.domain_id and principal.domain_id != domain_id:
            raise HTTPException(
                status_code=403, 
                detail="Access denied to this domain"
            )
        
        # Get graph integration instance
        graph_integration = get_graph_integration(domain_id)
        
        # Load existing graph if not already loaded
        if graph_integration.graph.number_of_nodes() == 0:
            logger.info(f"Loading existing graph for domain {domain_id}")
            graph_loaded = await graph_integration.load_existing_graph(domain_id)
            
            if not graph_loaded:
                logger.info(f"No existing graph found, building new graph for domain {domain_id}")
                build_result = await graph_integration.build_graph_from_chunks(domain_id)
                if build_result["status"] != "success":
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to build graph: {build_result.get('message', 'Unknown error')}"
                    )
        
        # Query the graph
        logger.info(f"Querying graph for domain {domain_id} with query: {query}")
        result = await graph_integration.query_graph(
            query=query,
            domain_id=domain_id,
            max_results=max_results
        )
        
        # Get graph statistics
        graph_stats = graph_integration.get_graph_statistics()
        
        if result["status"] == "success":
            return GraphQueryResponse(
                status="success",
                query=query,
                results=result["results"],
                total_found=result["total_found"],
                domain_id=domain_id,
                graph_stats=graph_stats,
                message=result.get("message")
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Graph query failed: {result.get('message', 'Unknown error')}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying graph for domain {domain_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.post("/query/{domain_id}", response_model=GraphQueryResponse)
async def query_graph_post(
    domain_id: int,
    request: GraphQueryRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal)
):
    """
    Query the knowledge graph using POST method (for complex queries)
    
    Args:
        domain_id: Domain ID to query
        request: Query request with query string and options
    
    Returns:
        Query results with graph relationships
    """
    
    return await query_graph(
        domain_id=domain_id,
        query=request.query,
        max_results=request.max_results,
        db=db,
        principal=principal
    )

@router.get("/stats/{domain_id}")
async def get_graph_statistics(
    domain_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal)
):
    """
    Get statistics about the knowledge graph for a domain
    
    Args:
        domain_id: Domain ID to get stats for
    
    Returns:
        Graph statistics
    """
    
    try:
        # Validate domain access (optional)
        if principal.domain_id and principal.domain_id != domain_id:
            raise HTTPException(
                status_code=403, 
                detail="Access denied to this domain"
            )
        
        # Get graph integration instance
        graph_integration = get_graph_integration(domain_id)
        
        # Load existing graph if not loaded
        if graph_integration.graph.number_of_nodes() == 0:
            graph_loaded = await graph_integration.load_existing_graph(domain_id)
            if not graph_loaded:
                return {
                    "domain_id": domain_id,
                    "status": "no_graph",
                    "message": "No graph exists for this domain",
                    "total_nodes": 0,
                    "total_edges": 0
                }
        
        # Get statistics
        stats = graph_integration.get_graph_statistics()
        stats["domain_id"] = domain_id
        stats["status"] = "success"
        
        return stats
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting graph stats for domain {domain_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

class GraphVisualizationRequest(BaseModel):
    query: str
    layout: str = "spring"
    node_size: int = 300
    font_size: int = 8

@router.post("/visualize/{domain_id}")
async def visualize_graph(
    domain_id: int,
    request: GraphVisualizationRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal)
):
    """
    Generate a graph visualization for a domain
    
    Args:
        domain_id: Domain ID to visualize graph for
        query: Query string to highlight relevant nodes
        layout: Layout algorithm (spring, kamada_kawai, circular)
        node_size: Size of nodes in visualization
        font_size: Font size for labels
    
    Returns:
        Visualization results with image path and stats
    """
    
    try:
        # Validate domain access (optional)
        if principal.domain_id and principal.domain_id != domain_id:
            raise HTTPException(
                status_code=403, 
                detail="Access denied to this domain"
            )
        
        # Get graph integration instance
        graph_integration = get_graph_integration(domain_id)
        
        # Load existing graph if not loaded
        if graph_integration.graph.number_of_nodes() == 0:
            logger.info(f"Loading existing graph for domain {domain_id}")
            graph_loaded = await graph_integration.load_existing_graph(domain_id)
            
            if not graph_loaded:
                logger.info(f"No existing graph found, building new graph for domain {domain_id}")
                build_result = await graph_integration.build_graph_from_chunks(domain_id)
                if build_result["status"] != "success":
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to build graph: {build_result.get('message', 'Unknown error')}"
                    )
        
        # Generate unique filename for this visualization
        import time
        timestamp = int(time.time())
        filename = f"graph_domain_{domain_id}_{timestamp}.png"
        file_path = os.path.join(graph_integration.output_dir, filename)
        
        # Generate the visualization
        logger.info(f"Generating graph visualization for domain {domain_id}")
        result = graph_integration.draw_graph(
            file_path=file_path,
            layout=request.layout,
            node_size=request.node_size,
            font_size=request.font_size
        )
        
        if result["status"] != "success":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate visualization: {result.get('message', 'Unknown error')}"
            )
        
        # Get graph statistics
        graph_stats = graph_integration.get_graph_statistics()
        
        return {
            "status": "success",
            "domain_id": domain_id,
            "query": request.query,
            "image_path": result["path"],
            "stats": graph_stats,
            "nodes": result["nodes"],
            "edges": result["edges"],
            "layout": request.layout,
            "message": "Graph visualization generated successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating graph visualization for domain {domain_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.delete("/reset/{domain_id}")
async def reset_graph(
    domain_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal)
):
    """
    Reset (clear) the knowledge graph for a domain
    
    Args:
        domain_id: Domain ID to reset graph for
    
    Returns:
        Reset confirmation
    """
    
    try:
        # Validate domain access (optional)
        if principal.domain_id and principal.domain_id != domain_id:
            raise HTTPException(
                status_code=403, 
                detail="Access denied to this domain"
            )
        
        # Get graph integration instance
        graph_integration = get_graph_integration(domain_id)
        
        # Clear the graph
        graph_integration.graph.clear()
        graph_integration.chunk_to_node_mapping.clear()
        
        # Remove saved graph file
        graph_file = os.path.join(graph_integration.output_dir, f"graph_domain_{domain_id}.json")
        if os.path.exists(graph_file):
            os.remove(graph_file)
        
        return {
            "status": "success",
            "domain_id": domain_id,
            "message": "Graph reset successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting graph for domain {domain_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )