"""
Graph Database Integration with RAG-Anything
Connects existing ChromaDB chunks to graph structure for enhanced RAG
"""

from __future__ import annotations
import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
import networkx as nx
import requests
from raganything import RAGAnything
from app.DB.db import get_db
from app.Models.tables import Chunk, Docs, Domain, User
from app.VectorDB.DB import vectorstore, search_similar_for_domain
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraphRAGIntegration:
    """
    Integrates RAG-Anything graph capabilities with existing ChromaDB chunks
    """
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "llama2", output_dir: str = "./graph_output"):
        """
        Initialize Graph RAG Integration with Ollama
        
        Args:
            ollama_url: Ollama server URL
            model: Ollama model name
            output_dir: Directory to store graph outputs
        """
        self.ollama_url = ollama_url
        self.model = model
        self.output_dir = output_dir
        self.rag = None  # Will be initialized when needed
        self.graph = nx.DiGraph()  # Directed graph for relationships
        self.chunk_to_node_mapping = {}  # Maps chunk IDs to graph nodes
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Check Ollama availability
        self._check_ollama_availability()
    
    def _check_ollama_availability(self) -> bool:
        """
        Check if Ollama server is available
        
        Returns:
            True if Ollama is available, False otherwise
        """
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [model["name"] for model in models]
                logger.info(f"Ollama server available at {self.ollama_url}")
                logger.info(f"Available models: {model_names}")
                
                if self.model not in model_names:
                    logger.warning(f"Model '{self.model}' not found. Available models: {model_names}")
                    if model_names:
                        self.model = model_names[0]  # Use first available model with full tag
                        logger.info(f"Using model: {self.model}")
                
                return True
            else:
                logger.error(f"Ollama server responded with status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama server not available at {self.ollama_url}: {e}")
            return False
    
    async def _initialize_rag(self):
        """
        Initialize RAG-Anything with Ollama configuration
        """
        if self.rag is None:
            try:
                logger.info(f"Initializing RAG-Anything with Ollama model: {self.model}")
                
                # Configure RAG-Anything for Ollama
                # Since RAG-Anything might not directly support Ollama, we'll use a custom approach
                # For now, we'll focus on the graph building without full RAG-Anything integration
                # and use Ollama API directly for any LLM operations
                
                self.rag = True  # Placeholder - we'll implement Ollama integration separately
                logger.info("RAG-Anything initialized for Ollama (custom implementation)")
                
            except Exception as e:
                logger.error(f"Failed to initialize RAG-Anything: {e}")
                raise
    
    async def _query_ollama(self, prompt: str) -> str:
        """
        Query Ollama directly for LLM operations
        
        Args:
            prompt: The prompt to send to Ollama
            
        Returns:
            Response from Ollama
        """
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return ""
                
        except Exception as e:
            logger.error(f"Error querying Ollama: {e}")
            return ""
        
    async def build_graph_from_chunks(
        self, 
        domain_id: int, 
        doc_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Build graph structure from existing chunks in ChromaDB
        
        Args:
            domain_id: Domain ID to filter chunks
            doc_id: Optional document ID to filter chunks
            user_id: Optional user ID to filter chunks
            
        Returns:
            Dictionary with graph statistics and metadata
        """
        logger.info(f"Building graph for domain_id={domain_id}, doc_id={doc_id}, user_id={user_id}")
        
        # Get database session
        db = next(get_db())
        
        try:
            # Query chunks from database
            query = """
                SELECT c.id, c.content, c.meta_data, c.doc_id, c.user_id, c.domain_id,
                       d.name as doc_name, u.username, dom.name as domain_name
                FROM chunks c
                JOIN docs d ON c.doc_id = d.id
                JOIN users u ON c.user_id = u.id
                JOIN domains dom ON c.domain_id = dom.id
                WHERE c.domain_id = :domain_id
            """
            params = {"domain_id": domain_id}
            
            if doc_id:
                query += " AND c.doc_id = :doc_id"
                params["doc_id"] = doc_id
                
            if user_id:
                query += " AND c.user_id = :user_id"
                params["user_id"] = user_id
                
            query += " ORDER BY c.id"
            
            result = db.execute(text(query), params)
            chunks = result.fetchall()
            
            logger.info(f"Found {len(chunks)} chunks to process")
            
            if not chunks:
                return {"status": "no_chunks", "message": "No chunks found for the given criteria"}
            
            # Process chunks and build graph
            graph_stats = await self._process_chunks_to_graph(chunks)
            
            # Save graph to file
            graph_file = os.path.join(self.output_dir, f"graph_domain_{domain_id}.json")
            await self._save_graph(graph_file)
            
            return {
                "status": "success",
                "chunks_processed": len(chunks),
                "nodes_created": graph_stats["nodes"],
                "edges_created": graph_stats["edges"],
                "graph_file": graph_file,
                "domain_id": domain_id,
                "doc_id": doc_id,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Error building graph: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            db.close()
    
    async def _process_chunks_to_graph(self, chunks: List[Tuple]) -> Dict[str, int]:
        """
        Process chunks and create graph nodes and edges
        
        Args:
            chunks: List of chunk tuples from database
            
        Returns:
            Dictionary with graph statistics
        """
        nodes_created = 0
        edges_created = 0
        
        # First pass: Create nodes for each chunk
        for chunk in chunks:
            chunk_id, content, meta_data, doc_id, user_id, domain_id, doc_name, username, domain_name = chunk
            
            # Parse metadata
            try:
                metadata = json.loads(meta_data) if meta_data else {}
            except:
                metadata = {}
            
            # Create node data
            node_data = {
                "chunk_id": chunk_id,
                "content": content,
                "doc_id": doc_id,
                "user_id": user_id,
                "domain_id": domain_id,
                "doc_name": doc_name,
                "username": username,
                "domain_name": domain_name,
                "metadata": metadata,
                "node_type": "chunk"
            }
            
            # Add node to graph
            node_id = f"chunk_{chunk_id}"
            self.graph.add_node(node_id, **node_data)
            self.chunk_to_node_mapping[chunk_id] = node_id
            nodes_created += 1
            
        # Second pass: Create edges based on content similarity
        await self._create_similarity_edges(chunks)
        
        # Third pass: Create document-level relationships
        await self._create_document_relationships(chunks)
        
        # Update edge count after creating edges
        edges_created = len(self.graph.edges())
        
        return {
            "nodes": nodes_created,
            "edges": len(self.graph.edges())
        }
    
    async def _create_similarity_edges(self, chunks: List[Tuple]) -> None:
        """
        Create edges between chunks based on content similarity using ChromaDB
        """
        logger.info("Creating similarity edges between chunks")
        
        for chunk in chunks:
            chunk_id, content, _, doc_id, user_id, domain_id, _, _, _ = chunk
            
            # Search for similar chunks using ChromaDB
            try:
                similar_docs = search_similar_for_domain(
                    query=content,
                    domain_id=domain_id,
                    k=5
                )
                
                # Create edges to similar chunks
                for similar_doc in similar_docs:
                    if hasattr(similar_doc, 'metadata') and 'chunk_id' in similar_doc.metadata:
                        similar_chunk_id = similar_doc.metadata['chunk_id']
                        if similar_chunk_id != chunk_id and similar_chunk_id in self.chunk_to_node_mapping:
                            source_node = self.chunk_to_node_mapping[chunk_id]
                            target_node = self.chunk_to_node_mapping[similar_chunk_id]
                            
                            # Add edge with similarity metadata
                            self.graph.add_edge(
                                source_node, 
                                target_node, 
                                edge_type="similarity",
                                weight=0.8  # Default similarity weight
                            )
                            
            except Exception as e:
                logger.warning(f"Error creating similarity edges for chunk {chunk_id}: {e}")
    
    async def _create_document_relationships(self, chunks: List[Tuple]) -> None:
        """
        Create relationships between chunks from the same document
        """
        logger.info("Creating document-level relationships")
        
        # Group chunks by document
        doc_chunks = {}
        for chunk in chunks:
            chunk_id, _, _, doc_id, _, _, _, _, _ = chunk
            if doc_id not in doc_chunks:
                doc_chunks[doc_id] = []
            doc_chunks[doc_id].append(chunk_id)
        
        # Create sequential relationships within documents
        for doc_id, chunk_ids in doc_chunks.items():
            if len(chunk_ids) > 1:
                # Sort chunks by ID to maintain order
                chunk_ids.sort()
                
                # Create sequential edges
                for i in range(len(chunk_ids) - 1):
                    source_chunk = chunk_ids[i]
                    target_chunk = chunk_ids[i + 1]
                    
                    if source_chunk in self.chunk_to_node_mapping and target_chunk in self.chunk_to_node_mapping:
                        source_node = self.chunk_to_node_mapping[source_chunk]
                        target_node = self.chunk_to_node_mapping[target_chunk]
                        
                        self.graph.add_edge(
                            source_node,
                            target_node,
                            edge_type="sequential",
                            weight=1.0
                        )
    
    async def _save_graph(self, file_path: str) -> None:
        """
        Save graph to JSON file
        """
        try:
            # Convert graph to JSON-serializable format
            graph_data = {
                "nodes": [
                    {
                        "id": node,
                        "data": data
                    }
                    for node, data in self.graph.nodes(data=True)
                ],
                "edges": [
                    {
                        "source": edge[0],
                        "target": edge[1],
                        "data": edge[2] if len(edge) > 2 else {}
                    }
                    for edge in self.graph.edges(data=True)
                ]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Graph saved to {file_path}")
            
        except Exception as e:
            logger.error(f"Error saving graph: {e}")
    
    async def query_graph(
        self, 
        query: str, 
        domain_id: int, 
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Query the graph for relevant information
        
        Args:
            query: Search query
            domain_id: Domain ID to filter results
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary with query results
        """
        logger.info(f"Querying graph for: {query}")
        
        try:
            # Check if graph has nodes
            if self.graph.number_of_nodes() == 0:
                logger.warning("Graph is empty, cannot query")
                return {
                    "status": "success",
                    "query": query,
                    "results": [],
                    "total_found": 0,
                    "message": "Graph is empty"
                }
            
            # First, try to find chunks by content similarity in the graph
            logger.info("Searching graph nodes by content similarity")
            relevant_chunk_ids = []
            
            # Get all nodes and search by content similarity
            for node_id, node_data in self.graph.nodes(data=True):
                if node_data.get("domain_id") == domain_id:
                    content = node_data.get("content", "").lower()
                    query_lower = query.lower()
                    
                    # Simple content matching
                    if (query_lower in content or 
                        any(word in content for word in query_lower.split() if len(word) > 3)):
                        relevant_chunk_ids.append(node_data.get("chunk_id"))
                        logger.info(f"Found matching chunk {node_data.get('chunk_id')}: {content[:50]}...")
            
            # If still no results, try ChromaDB as fallback
            if not relevant_chunk_ids:
                logger.info("No matches in graph, trying ChromaDB")
                similar_chunks = search_similar_for_domain(
                    query=query,
                    domain_id=domain_id,
                    k=max_results
                )
                
                # Extract chunk IDs from similar chunks
                for chunk in similar_chunks:
                    if hasattr(chunk, 'metadata') and 'chunk_id' in chunk.metadata:
                        relevant_chunk_ids.append(chunk.metadata['chunk_id'])
                    elif hasattr(chunk, 'metadata') and 'id' in chunk.metadata:
                        relevant_chunk_ids.append(chunk.metadata['id'])
            
            # Find related nodes in graph
            related_nodes = []
            for chunk_id in relevant_chunk_ids:
                if chunk_id in self.chunk_to_node_mapping:
                    node_id = self.chunk_to_node_mapping[chunk_id]
                    node_data = self.graph.nodes[node_id]
                    related_nodes.append({
                        "chunk_id": chunk_id,
                        "content": node_data["content"],
                        "doc_name": node_data["doc_name"],
                        "metadata": node_data["metadata"]
                    })
                    
                    # Find connected nodes (neighbors)
                    neighbors = list(self.graph.neighbors(node_id))
                    for neighbor_id in neighbors[:3]:  # Limit to 3 neighbors
                        neighbor_data = self.graph.nodes[neighbor_id]
                        related_nodes.append({
                            "chunk_id": neighbor_data["chunk_id"],
                            "content": neighbor_data["content"],
                            "doc_name": neighbor_data["doc_name"],
                            "metadata": neighbor_data["metadata"],
                            "relationship": "connected"
                        })
            
            return {
                "status": "success",
                "query": query,
                "results": related_nodes[:max_results],
                "total_found": len(related_nodes)
            }
            
        except Exception as e:
            logger.error(f"Error querying graph: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the current graph
        
        Returns:
            Dictionary with graph statistics
        """
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_types": self._count_node_types(),
            "edge_types": self._count_edge_types(),
            "connected_components": nx.number_weakly_connected_components(self.graph)
        }
    
    def _count_node_types(self) -> Dict[str, int]:
        """Count different types of nodes"""
        node_types = {}
        for _, data in self.graph.nodes(data=True):
            node_type = data.get("node_type", "unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1
        return node_types
    
    def _count_edge_types(self) -> Dict[str, int]:
        """Count different types of edges"""
        edge_types = {}
        for _, _, data in self.graph.edges(data=True):
            edge_type = data.get("edge_type", "unknown")
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
        return edge_types
    
    async def update_graph_with_new_chunks(
        self, 
        domain_id: int, 
        doc_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Incrementally update the graph with new chunks from a specific document
        
        Args:
            domain_id: Domain ID
            doc_id: Document ID to add chunks from
            user_id: User ID
            
        Returns:
            Update results
        """
        logger.info(f"Updating graph with new chunks for doc_id={doc_id}, domain_id={domain_id}")
        
        # Get database session
        db = next(get_db())
        
        try:
            # Query only the new chunks for this document
            query = """
                SELECT c.id, c.content, c.meta_data, c.doc_id, c.user_id, c.domain_id,
                       d.name as doc_name, u.username, dom.name as domain_name
                FROM chunks c
                JOIN docs d ON c.doc_id = d.id
                JOIN users u ON c.user_id = u.id
                JOIN domains dom ON c.domain_id = dom.id
                WHERE c.domain_id = :domain_id AND c.doc_id = :doc_id
                ORDER BY c.id
            """
            
            result = db.execute(text(query), {"domain_id": domain_id, "doc_id": doc_id})
            new_chunks = result.fetchall()
            
            logger.info(f"Found {len(new_chunks)} new chunks to add to graph")
            
            if not new_chunks:
                return {"status": "no_chunks", "message": "No new chunks found for this document"}
            
            # Add new nodes to existing graph
            nodes_added = 0
            for chunk in new_chunks:
                chunk_id, content, meta_data, doc_id, user_id, domain_id, doc_name, username, domain_name = chunk
                
                # Skip if chunk already exists in graph
                if chunk_id in self.chunk_to_node_mapping:
                    continue
                
                # Parse metadata
                try:
                    metadata = json.loads(meta_data) if meta_data else {}
                except:
                    metadata = {}
                
                # Create node data
                node_data = {
                    "chunk_id": chunk_id,
                    "content": content,
                    "doc_id": doc_id,
                    "user_id": user_id,
                    "domain_id": domain_id,
                    "doc_name": doc_name,
                    "username": username,
                    "domain_name": domain_name,
                    "metadata": metadata,
                    "node_type": "chunk"
                }
                
                # Add node to graph
                node_id = f"chunk_{chunk_id}"
                self.graph.add_node(node_id, **node_data)
                self.chunk_to_node_mapping[chunk_id] = node_id
                nodes_added += 1
            
            # Create relationships for new chunks
            await self._create_similarity_edges(new_chunks)
            await self._create_document_relationships(new_chunks)
            
            # Save updated graph
            graph_file = os.path.join(self.output_dir, f"graph_domain_{domain_id}.json")
            await self._save_graph(graph_file)
            
            return {
                "status": "success",
                "chunks_processed": len(new_chunks),
                "nodes_added": nodes_added,
                "total_nodes": self.graph.number_of_nodes(),
                "total_edges": self.graph.number_of_edges(),
                "graph_file": graph_file
            }
            
        except Exception as e:
            logger.error(f"Error updating graph: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            db.close()
    
    async def load_existing_graph(self, domain_id: int) -> bool:
        """
        Load existing graph from saved file
        
        Args:
            domain_id: Domain ID
            
        Returns:
            True if graph loaded successfully, False otherwise
        """
        graph_file = os.path.join(self.output_dir, f"graph_domain_{domain_id}.json")
        
        if not os.path.exists(graph_file):
            logger.info(f"No existing graph file found at {graph_file}")
            return False
        
        try:
            with open(graph_file, 'r', encoding='utf-8') as f:
                graph_data = json.load(f)
            
            # Clear existing graph
            self.graph.clear()
            self.chunk_to_node_mapping.clear()
            
            # Load nodes
            for node_data in graph_data.get("nodes", []):
                node_id = node_data["id"]
                data = node_data["data"]
                self.graph.add_node(node_id, **data)
                
                # Update chunk mapping
                if "chunk_id" in data:
                    self.chunk_to_node_mapping[data["chunk_id"]] = node_id
            
            # Load edges
            for edge_data in graph_data.get("edges", []):
                source = edge_data["source"]
                target = edge_data["target"]
                data = edge_data.get("data", {})
                self.graph.add_edge(source, target, **data)
            
            logger.info(f"Loaded existing graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
            return True
            
        except Exception as e:
            logger.error(f"Error loading existing graph: {e}")
            return False

    async def delete_chunks_for_document(self, domain_id: int, doc_id: int) -> Dict[str, Any]:
        """
        Deletes all chunks associated with a specific document from the graph.

        Args:
            domain_id: The ID of the domain the document belongs to.
            doc_id: The ID of the document whose chunks are to be deleted.

        Returns:
            A dictionary indicating the status and number of chunks deleted.
        """
        logger.info(f"Attempting to delete chunks for document {doc_id} in domain {domain_id}")
        
        # Load the existing graph for the domain
        if not await self.load_existing_graph(domain_id):
            return {"status": "error", "message": f"Failed to load graph for domain {domain_id}"}

        chunks_deleted = 0
        nodes_to_remove = []

        # Identify nodes to remove
        for node_id, data in list(self.graph.nodes(data=True)):
            if data.get("node_type") == "chunk" and data.get("doc_id") == doc_id:
                nodes_to_remove.append(node_id)
                if "chunk_id" in data and data["chunk_id"] in self.chunk_to_node_mapping:
                    del self.chunk_to_node_mapping[data["chunk_id"]]

        # Remove identified nodes and their incident edges
        self.graph.remove_nodes_from(nodes_to_remove)
        chunks_deleted = len(nodes_to_remove)

        # Save the updated graph
        graph_file = os.path.join(self.output_dir, f"graph_domain_{domain_id}.json")
        await self._save_graph(graph_file)
        
        logger.info(f"Deleted {chunks_deleted} chunks for document {doc_id} in domain {domain_id}")
        return {"status": "success", "chunks_deleted": chunks_deleted}


# Utility functions for easy integration
async def build_domain_graph(domain_id: int, ollama_url: str = "http://localhost:11434", model: str = "llama2") -> Dict[str, Any]:
    """
    Convenience function to build graph for entire domain
    
    Args:
        domain_id: Domain ID
        ollama_url: Ollama server URL
        model: Ollama model name
        
    Returns:
        Graph building results
    """
    graph_integration = GraphRAGIntegration(ollama_url=ollama_url, model=model)
    return await graph_integration.build_graph_from_chunks(domain_id=domain_id)

async def query_domain_graph(query: str, domain_id: int, ollama_url: str = "http://localhost:11434", model: str = "llama2") -> Dict[str, Any]:
    """
    Convenience function to query domain graph
    
    Args:
        query: Search query
        domain_id: Domain ID
        ollama_url: Ollama server URL
        model: Ollama model name
        
    Returns:
        Query results
    """
    graph_integration = GraphRAGIntegration(ollama_url=ollama_url, model=model)
    return await graph_integration.query_graph(query, domain_id)
