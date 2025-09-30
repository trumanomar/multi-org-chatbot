"""
Graph Database Integration with RAG-Anything
Enhanced with automated triplet extraction and reasoning
FIXED VERSION with better error handling and logging
"""

from __future__ import annotations
import os
import json
import asyncio
import re
from typing import List, Dict, Any, Optional, Tuple, Set
from sqlalchemy.orm import Session
from sqlalchemy import text
import networkx as nx
import requests
from raganything import RAGAnything
from app.DB.db import get_db
from app.Models.tables import Chunk, Docs, Domain, User
from app.VectorDB.DB import vectorstore, search_similar_for_domain
import logging
from typing import cast
import traceback

try:
    import matplotlib.pyplot as plt  # type: ignore
except Exception:
    plt = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraphRAGIntegration:
    """
    Integrates RAG-Anything graph capabilities with existing ChromaDB chunks
    """

    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "llama3.1:8b-instruct-q4_K_M", output_dir: str = "./graph_output"):
        """Initialize Graph RAG Integration with Ollama"""
        self.ollama_url = ollama_url
        self.model = model
        self.output_dir = output_dir
        self.rag = None
        self.graph = nx.DiGraph()
        self.chunk_to_node_mapping = {}

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"✅ Graph output directory created/verified: {output_dir}")
        
        self._check_ollama_availability()

    def _check_ollama_availability(self) -> bool:
        """Check if Ollama server is available"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [model["name"] for model in models]
                logger.info(f"✅ Ollama server available at {self.ollama_url}")
                logger.info(f"Available models: {model_names}")

                if self.model not in model_names:
                    logger.warning(f"⚠️ Model '{self.model}' not found. Available models: {model_names}")
                    if model_names:
                        self.model = model_names[0]
                        logger.info(f"Using model: {self.model}")
                return True
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Ollama server not available at {self.ollama_url}: {e}")
            logger.warning("⚠️ Continuing without triplet extraction (Ollama not available)")
            return False

    async def _query_ollama(self, prompt: str, temperature: float = 0.3) -> str:
        """Query Ollama directly for LLM operations"""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": temperature,
                    "options": {"num_predict": 500}
                },
                timeout=60
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

    async def extract_triplets_from_text(self, text: str, max_triplets: int = 20) -> List[Dict[str, str]]:
        """Extract knowledge triplets from text using LLM"""
        prompt = f"""Extract knowledge triplets from the following text. 
Each triplet should be in the format (subject, predicate, object).
Only extract clear, factual relationships. Limit to {max_triplets} most important triplets.

Format your response as a JSON array like this:
[
{{"subject": "Dr. Alice", "predicate": "founded", "object": "MedCare Hospital"}},
{{"subject": "Dr. Bob", "predicate": "works_at", "object": "MedCare Hospital"}}
]

Text: {text}

JSON array of triplets:"""

        response = await self._query_ollama(prompt, temperature=0.1)

        try:
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                triplets = json.loads(json_match.group())
                valid_triplets = []
                for t in triplets:
                    if isinstance(t, dict) and "subject" in t and "predicate" in t and "object" in t:
                        valid_triplets.append({
                            "subject": str(t["subject"]).strip(),
                            "predicate": str(t["predicate"]).strip().lower().replace(" ", "_"),
                            "object": str(t["object"]).strip()
                        })
                return valid_triplets[:max_triplets]
        except Exception as e:
            logger.warning(f"Failed to parse triplets from LLM response: {e}")

        return []

    async def update_graph_with_new_chunks(self, domain_id: int, doc_id: int, user_id: int, extract_triplets: bool = True) -> Dict[str, Any]:
        """Incrementally update the graph with new chunks"""
        logger.info(f"🔄 Updating graph with new chunks for doc_id={doc_id}, domain_id={domain_id}")

        # Load existing graph first
        loaded = await self.load_existing_graph(domain_id)
        logger.info(f"Graph loaded: {loaded}, Current nodes: {self.graph.number_of_nodes()}, edges: {self.graph.number_of_edges()}")

        db = next(get_db())

        try:
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

            logger.info(f"📊 Found {len(new_chunks)} chunks for doc_id={doc_id}")

            if not new_chunks:
                logger.warning(f"⚠️ No chunks found for doc_id={doc_id}, domain_id={domain_id}")
                return {"status": "no_chunks", "message": "No new chunks found for this document"}

            nodes_added = 0
            triplets_extracted = 0

            for chunk in new_chunks:
                chunk_id, content, meta_data, doc_id, user_id, domain_id, doc_name, username, domain_name = chunk

                # Skip if already exists
                if chunk_id in self.chunk_to_node_mapping:
                    logger.debug(f"Skipping chunk {chunk_id} - already in graph")
                    continue

                try:
                    metadata = json.loads(meta_data) if meta_data else {}
                except Exception:
                    metadata = {}

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

                node_id = f"chunk_{chunk_id}"
                self.graph.add_node(node_id, **node_data)
                self.chunk_to_node_mapping[chunk_id] = node_id
                nodes_added += 1
                logger.debug(f"✅ Added node: {node_id}")

                # Extract triplets
                if extract_triplets and content and len(content) > 50:
                    try:
                        triplets = await self.extract_triplets_from_text(content)
                        for triplet in triplets:
                            self.add_triplet_by_names(
                                subject_name=triplet["subject"],
                                predicate=triplet["predicate"],
                                object_name=triplet["object"],
                                extra_data={"source_chunk_id": chunk_id}
                            )
                            triplets_extracted += 1
                        logger.debug(f"📝 Extracted {len(triplets)} triplets from chunk {chunk_id}")
                    except Exception as e:
                        logger.error(f"Error extracting triplets from chunk {chunk_id}: {e}")

            # Save updated graph
            graph_file = os.path.join(self.output_dir, f"graph_domain_{domain_id}.json")
            logger.info(f"💾 Saving graph to: {graph_file}")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(graph_file), exist_ok=True)
            
            await self._save_graph(graph_file)
            
            # Verify file was created
            if os.path.exists(graph_file):
                file_size = os.path.getsize(graph_file)
                logger.info(f"✅ Graph file saved successfully: {graph_file} ({file_size} bytes)")
            else:
                logger.error(f"❌ Graph file was NOT created: {graph_file}")

            final_stats = {
                "status": "success",
                "chunks_processed": len(new_chunks),
                "nodes_added": nodes_added,
                "triplets_extracted": triplets_extracted,
                "total_nodes": self.graph.number_of_nodes(),
                "total_edges": self.graph.number_of_edges(),
                "graph_file": graph_file,
                "graph_file_exists": os.path.exists(graph_file)
            }
            
            logger.info(f"✅ Graph update complete: {final_stats}")
            return final_stats

        except Exception as e:
            logger.error(f"❌ Error updating graph: {e}")
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
        finally:
            db.close()

    async def build_graph_from_chunks(
        self,
        domain_id: int,
        doc_id: Optional[int] = None,
        user_id: Optional[int] = None,
        extract_triplets: bool = True
    ) -> Dict[str, Any]:
        """Build graph structure from existing chunks in ChromaDB"""
        logger.info(f"🏗️ Building graph for domain_id={domain_id}, extract_triplets={extract_triplets}")

        db = next(get_db())

        try:
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

            logger.info(f"📊 Found {len(chunks)} chunks to process")

            if not chunks:
                logger.warning("⚠️ No chunks found")
                return {"status": "no_chunks", "message": "No chunks found for the given criteria"}

            # Create chunk nodes
            graph_stats = await self._process_chunks_to_graph(chunks)

            # Extract triplets from each chunk
            triplets_extracted = 0
            if extract_triplets:
                logger.info("🔍 Extracting triplets from chunks using LLM...")
                for chunk in chunks:
                    chunk_id, content, *_ = chunk
                    if content and len(content) > 50:
                        triplets = await self.extract_triplets_from_text(content)

                        for triplet in triplets:
                            self.add_triplet_by_names(
                                subject_name=triplet["subject"],
                                predicate=triplet["predicate"],
                                object_name=triplet["object"],
                                extra_data={"source_chunk_id": chunk_id}
                            )
                            triplets_extracted += 1

            # Save updated graph
            graph_file = os.path.join(self.output_dir, f"graph_domain_{domain_id}.json")
            logger.info(f"💾 Saving graph to: {graph_file}")
            await self._save_graph(graph_file)
            
            # Verify
            if os.path.exists(graph_file):
                logger.info(f"✅ Graph file created: {graph_file}")
            else:
                logger.error(f"❌ Graph file NOT created: {graph_file}")

            return {
                "status": "success",
                "chunks_processed": len(chunks),
                "nodes_created": graph_stats["nodes"],
                "edges_created": self.graph.number_of_edges(),
                "triplets_extracted": triplets_extracted,
                "graph_file": graph_file,
                "domain_id": domain_id
            }

        except Exception as e:
            logger.error(f"❌ Error building graph: {e}")
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
        finally:
            db.close()

    async def _process_chunks_to_graph(self, chunks: List[Tuple]) -> Dict[str, int]:
        """Process chunks and create graph nodes"""
        nodes_created = 0

        for chunk in chunks:
            chunk_id, content, meta_data, doc_id, user_id, domain_id, doc_name, username, domain_name = chunk

            try:
                metadata = json.loads(meta_data) if meta_data else {}
            except Exception:
                metadata = {}

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

            node_id = f"chunk_{chunk_id}"
            self.graph.add_node(node_id, **node_data)
            self.chunk_to_node_mapping[chunk_id] = node_id
            nodes_created += 1

        logger.info(f"✅ Created {nodes_created} nodes")
        return {"nodes": nodes_created, "edges": self.graph.number_of_edges()}

    def add_triplet(
        self,
        subject_chunk_id: int,
        predicate: str,
        object_chunk_id: int,
        weight: float = 1.0,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create a triplet edge between two chunk nodes"""
        if subject_chunk_id not in self.chunk_to_node_mapping or object_chunk_id not in self.chunk_to_node_mapping:
            logger.warning(f"Cannot add triplet; missing nodes for subject={subject_chunk_id}, object={object_chunk_id}")
            return False

        subject_node = self.chunk_to_node_mapping[subject_chunk_id]
        object_node = self.chunk_to_node_mapping[object_chunk_id]

        edge_attrs: Dict[str, Any] = {
            "edge_type": "triplet",
            "predicate": predicate,
            "weight": weight,
        }
        if extra_data:
            edge_attrs.update(extra_data)

        self.graph.add_edge(subject_node, object_node, **edge_attrs)
        return True

    def add_entity(
        self,
        name: str,
        node_type: str = "entity",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Ensure an entity/literal node exists and return its node id"""
        prefix = "literal" if node_type == "literal" else "entity"
        node_id = f"{prefix}:{name}"
        if not self.graph.has_node(node_id):
            node_data: Dict[str, Any] = {
                "node_type": node_type,
                "label": name,
            }
            if metadata:
                node_data.update(metadata)
            self.graph.add_node(node_id, **node_data)
        return node_id

    def add_triplet_by_names(
        self,
        subject_name: str,
        predicate: str,
        object_name: str,
        object_is_literal: bool = False,
        weight: float = 1.0,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create a triplet using entity/literal names"""
        subject_id = self.add_entity(subject_name, node_type="entity")
        object_type = "literal" if object_is_literal else "entity"
        object_id = self.add_entity(object_name, node_type=object_type)

        edge_attrs: Dict[str, Any] = {
            "edge_type": "triplet",
            "predicate": predicate,
            "weight": weight,
        }
        if extra_data:
            edge_attrs.update(extra_data)

        self.graph.add_edge(subject_id, object_id, **edge_attrs)
        return True

    def get_triplets_for_entity(self, name: str) -> Dict[str, List[Dict[str, Any]]]:
        """Return outgoing and incoming triplets for an entity by name"""
        results: Dict[str, List[Dict[str, Any]]] = {"out": [], "in": []}
        for node_id, data in self.graph.nodes(data=True):
            if data.get("label") == name:
                for _, v, edata in self.graph.out_edges(node_id, data=True):
                    if edata.get("edge_type") == "triplet":
                        results["out"].append({
                            "subject": data.get("label", node_id),
                            "predicate": edata.get("predicate"),
                            "object": self.graph.nodes[v].get("label", v),
                        })
                for u, _, edata in self.graph.in_edges(node_id, data=True):
                    if edata.get("edge_type") == "triplet":
                        results["in"].append({
                            "subject": self.graph.nodes[u].get("label", u),
                            "predicate": edata.get("predicate"),
                            "object": data.get("label", node_id),
                        })
        return results

    def query_triplets(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query triplets by pattern. Any parameter can be None (wildcard)"""
        matches: List[Dict[str, Any]] = []

        def node_matches(node_id: str, name: Optional[str]) -> bool:
            if name is None:
                return True
            data = self.graph.nodes[node_id]
            label = data.get("label") or (str(data.get("chunk_id")) if data.get("chunk_id") is not None else None)
            return label == name

        for u, v, edata in self.graph.edges(data=True):
            if edata.get("edge_type") != "triplet":
                continue
            if predicate is not None and edata.get("predicate") != predicate:
                continue
            if not node_matches(u, subject):
                continue
            if not node_matches(v, object):
                continue
            matches.append({
                "subject": self.graph.nodes[u].get("label", u),
                "predicate": edata.get("predicate"),
                "object": self.graph.nodes[v].get("label", v),
            })
        return matches

    async def query_graph(
        self,
        query: str,
        domain_id: int,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """Query the graph for relevant information"""
        logger.info(f"🔍 Querying graph for: '{query}' in domain {domain_id}")
        logger.info(f"Current graph state: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")

        try:
            if self.graph.number_of_nodes() == 0:
                logger.warning("⚠️ Graph is empty, loading from file...")
                loaded = await self.load_existing_graph(domain_id)
                if not loaded or self.graph.number_of_nodes() == 0:
                    logger.warning("❌ Graph is still empty after loading")
                    return {
                        "status": "success",
                        "query": query,
                        "results": [],
                        "total_found": 0,
                        "message": "Graph is empty. Please build the graph first using build_graph_from_chunks()."
                    }
                logger.info(f"✅ Graph loaded: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")

            results: List[Dict[str, Any]] = []
            query_lower = query.lower()

            # 1) Chunk content matching
            chunk_matches = 0
            for node_id, node_data in self.graph.nodes(data=True):
                if node_data.get("node_type") == "chunk" and node_data.get("domain_id") == domain_id:
                    content = (node_data.get("content") or "").lower()
                    if (query_lower in content or any(word in content for word in query_lower.split() if len(word) > 3)):
                        results.append({
                            "chunk_id": node_data.get("chunk_id"),
                            "content": node_data.get("content", ""),
                            "doc_name": node_data.get("doc_name"),
                            "metadata": node_data.get("metadata", {}),
                            "match": "chunk_content"
                        })
                        chunk_matches += 1

            logger.info(f"📊 Found {chunk_matches} chunk content matches")

            # 2) Triplet/entity matching
            tokens = [w for w in query_lower.split() if len(w) > 2]
            matched_nodes: List[str] = []
            for node_id, node_data in self.graph.nodes(data=True):
                if node_data.get("node_type") in ("entity", "literal"):
                    label = (node_data.get("label") or "").lower()
                    if label and ((query_lower in label) or any(t in label for t in tokens)):
                        matched_nodes.append(node_id)

            logger.info(f"📊 Found {len(matched_nodes)} entity/literal matches")

            # Collect triplet edges
            triplet_matches = 0
            for node_id in matched_nodes:
                for _, v, edata in self.graph.out_edges(node_id, data=True):
                    if edata.get("edge_type") == "triplet":
                        subj = self.graph.nodes[node_id].get("label", node_id)
                        obj = self.graph.nodes[v].get("label", v)
                        pred = edata.get("predicate")
                        results.append({
                            "content": f"{subj} -[{pred}]-> {obj}",
                            "metadata": {"type": "triplet", "subject": subj, "predicate": pred, "object": obj},
                            "match": "triplet_label"
                        })
                        triplet_matches += 1
                for u, _, edata in self.graph.in_edges(node_id, data=True):
                    if edata.get("edge_type") == "triplet":
                        subj = self.graph.nodes[u].get("label", u)
                        obj = self.graph.nodes[node_id].get("label", node_id)
                        pred = edata.get("predicate")
                        results.append({
                            "content": f"{subj} -[{pred}]-> {obj}",
                            "metadata": {"type": "triplet", "subject": subj, "predicate": pred, "object": obj},
                            "match": "triplet_label"
                        })
                        triplet_matches += 1

            logger.info(f"📊 Found {triplet_matches} triplet matches")
            logger.info(f"✅ Total results: {len(results)}")

            return {
                "status": "success",
                "query": query,
                "results": results[:max_results],
                "total_found": len(results),
                "stats": {
                    "chunk_matches": chunk_matches,
                    "triplet_matches": triplet_matches,
                    "total_nodes": self.graph.number_of_nodes(),
                    "total_edges": self.graph.number_of_edges()
                }
            }

        except Exception as e:
            logger.error(f"❌ Error querying graph: {e}")
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    async def query_vector(self, query: str, domain_id: int, k: int = 10) -> Dict[str, Any]:
        """Query vector database only"""
        try:
            similar_chunks = search_similar_for_domain(query=query, domain_id=domain_id, k=k)
            vector_results: List[Dict[str, Any]] = []
            for item in similar_chunks:
                meta = getattr(item, "metadata", {}) or {}
                content = getattr(item, "page_content", None)
                if content is None:
                    content = getattr(item, "content", None)
                score = getattr(item, "score", None)

                vector_results.append({
                    "chunk_id": meta.get("chunk_id") or meta.get("id"),
                    "content": content,
                    "metadata": meta,
                    "score": score,
                })

            return {
                "status": "success",
                "query": query,
                "results": vector_results[:k],
                "total_found": len(vector_results),
            }
        except Exception as e:
            logger.error(f"Error querying vector DB: {e}")
            return {"status": "error", "message": str(e)}

    async def query_separate(self, query: str, domain_id: int, k: int = 10) -> Dict[str, Any]:
        """Run vector and graph queries separately"""
        logger.info(f"🔍 Running separate vector + graph query for: '{query}'")
        
        vector = await self.query_vector(query=query, domain_id=domain_id, k=k)
        graph = await self.query_graph(query=query, domain_id=domain_id, max_results=k)

        return {
            "status": "success",
            "query": query,
            "vector": vector.get("results", []) if vector.get("status") == "success" else [],
            "graph": graph.get("results", []) if graph.get("status") == "success" else [],
            "vector_total": vector.get("total_found", 0) if vector.get("status") == "success" else 0,
            "graph_total": graph.get("total_found", 0) if graph.get("status") == "success" else 0,
        }

    def draw_graph(self, file_path: Optional[str] = None, layout: str = "spring", node_size: int = 300, font_size: int = 6) -> Dict[str, Any]:
        """Draw and save the graph visualization"""
        if plt is None:
            return {"status": "error", "message": "matplotlib is not installed"}

        if self.graph.number_of_nodes() == 0:
            return {"status": "error", "message": "graph is empty"}

        if layout == "spring":
            pos = nx.spring_layout(self.graph, seed=42)
        elif layout == "kamada_kawai":
            pos = nx.kamada_kawai_layout(self.graph)
        elif layout == "circular":
            pos = nx.circular_layout(self.graph)
        else:
            pos = nx.spring_layout(self.graph, seed=42)

        edge_colors = []
        for u, v, data in self.graph.edges(data=True):
            edge_type = cast(Dict[str, Any], data).get("edge_type", "unknown")
            if edge_type == "similarity":
                edge_colors.append("#1f77b4")
            elif edge_type == "sequential":
                edge_colors.append("#2ca02c")
            elif edge_type == "triplet":
                edge_colors.append("#d62728")
            else:
                edge_colors.append("#7f7f7f")

        labels = {}
        for node_id, data in self.graph.nodes(data=True):
            if data.get("node_type") in ("entity", "literal"):
                labels[node_id] = data.get("label", node_id)[:20]
            else:
                labels[node_id] = str(data.get("chunk_id", node_id))

        plt.figure(figsize=(14, 10))
        nx.draw_networkx_nodes(self.graph, pos, node_size=node_size, node_color="#ddddff", linewidths=0.5, edgecolors="#333333")
        nx.draw_networkx_edges(self.graph, pos, edge_color=edge_colors, arrows=True, arrowstyle="->", arrowsize=10, width=1.0)
        nx.draw_networkx_labels(self.graph, pos, labels=labels, font_size=font_size)

        edge_labels = {}
        for u, v, data in self.graph.edges(data=True):
            if data.get("edge_type") == "triplet":
                edge_labels[(u, v)] = data.get("predicate", "triplet")

        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels=edge_labels, font_size=max(5, font_size - 1))

        plt.axis("off")
        out_path = file_path or os.path.join(self.output_dir, "graph.png")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        plt.tight_layout()
        plt.savefig(out_path, dpi=200)
        plt.close()

        return {"status": "success", "path": out_path, "nodes": self.graph.number_of_nodes(), "edges": self.graph.number_of_edges()}

    async def _save_graph(self, file_path: str) -> None:
        """Save graph to JSON file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            graph_data = {
                "nodes": [{"id": node, "data": data} for node, data in self.graph.nodes(data=True)],
                "edges": [{"source": edge[0], "target": edge[1], "data": edge[2] if len(edge) > 2 else {}} for edge in self.graph.edges(data=True)]
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ Graph saved to {file_path} ({len(graph_data['nodes'])} nodes, {len(graph_data['edges'])} edges)")
        except Exception as e:
            logger.error(f"❌ Error saving graph: {e}")
            traceback.print_exc()
            raise

    async def load_existing_graph(self, domain_id: int) -> bool:
        """Load existing graph from saved file"""
        graph_file = os.path.join(self.output_dir, f"graph_domain_{domain_id}.json")

        if not os.path.exists(graph_file):
            logger.info(f"No existing graph file found at {graph_file}")
            return False

        try:
            with open(graph_file, 'r', encoding='utf-8') as f:
                graph_data = json.load(f)

            self.graph.clear()
            self.chunk_to_node_mapping.clear()

            for node_data in graph_data.get("nodes", []):
                node_id = node_data["id"]
                data = node_data["data"]
                self.graph.add_node(node_id, **data)

                if "chunk_id" in data:
                    self.chunk_to_node_mapping[data["chunk_id"]] = node_id

            for edge_data in graph_data.get("edges", []):
                source = edge_data["source"]
                target = edge_data["target"]
                data = edge_data.get("data", {})
                self.graph.add_edge(source, target, **data)

            logger.info(f"✅ Loaded existing graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
            return True

        except Exception as e:
            logger.error(f"❌ Error loading existing graph: {e}")
            traceback.print_exc()
            return False

    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get statistics about the current graph"""
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


# Utility functions for easy integration

async def build_domain_graph(domain_id: int, ollama_url: str = "http://localhost:11434", model: str = "llama3.1:8b-instruct-q4_K_M", extract_triplets: bool = True) -> Dict[str, Any]:
    """
    Convenience function to build graph for entire domain

    Args:
        domain_id: Domain ID
        ollama_url: Ollama server URL
        model: Ollama model name
        extract_triplets: Whether to automatically extract triplets using LLM

    Returns:
        Graph building results
    """
    graph_integration = GraphRAGIntegration(ollama_url=ollama_url, model=model)
    return await graph_integration.build_graph_from_chunks(domain_id=domain_id, extract_triplets=extract_triplets)

async def query_domain_graph(query: str, domain_id: int, ollama_url: str = "http://localhost:11434", model: str = "llama3.1:8b-instruct-q4_K_M") -> Dict[str, Any]:
    """
    Convenience function to query domain graph

    IMPORTANT: This function automatically loads the existing graph before querying.

    Args:
        query: Search query
        domain_id: Domain ID
        ollama_url: Ollama server URL
        model: Ollama model name

    Returns:
        Query results
    """
    graph_integration = GraphRAGIntegration(ollama_url=ollama_url, model=model)

    # CRITICAL: Load the existing graph first
    loaded = await graph_integration.load_existing_graph(domain_id)

    if not loaded:
        logger.warning(f"No existing graph found for domain {domain_id}. Build the graph first using build_domain_graph().")
        return {
            "status": "error",
            "message": f"No graph found for domain {domain_id}. Please build the graph first.",
            "results": [],
            "total_found": 0
        }

    return await graph_integration.query_graph(query, domain_id)

async def query_domain_graph_separate(query: str, domain_id: int, ollama_url: str = "http://localhost:11434", model: str = "llama3.1:8b-instruct-q4_K_M", k: int = 10) -> Dict[str, Any]:
    """
    Convenience function to query both vector and graph separately

    Args:
        query: Search query
        domain_id: Domain ID
        ollama_url: Ollama server URL
        model: Ollama model name
        k: Number of results to return

    Returns:
        Combined results from vector and graph queries
    """
    graph_integration = GraphRAGIntegration(ollama_url=ollama_url, model=model)

    # Load the existing graph first
    await graph_integration.load_existing_graph(domain_id)

    return await graph_integration.query_separate(query, domain_id, k=k)