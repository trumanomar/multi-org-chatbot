"""
Graph Database Configuration
Settings for RAG-Anything graph integration
"""

import os
from typing import Optional

# Graph Database Settings
GRAPH_OUTPUT_DIR = os.getenv("GRAPH_OUTPUT_DIR", "./graph_output")
GRAPH_CACHE_DIR = os.getenv("GRAPH_CACHE_DIR", "./graph_cache")

# RAG-Anything Settings (Ollama)
RAG_ANYTHING_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")  # Ollama doesn't require API key
RAG_ANYTHING_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")  # Default Ollama model

# Graph Processing Settings
MAX_CHUNKS_PER_BATCH = int(os.getenv("MAX_CHUNKS_PER_BATCH", "1000"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))
MAX_SIMILAR_CHUNKS = int(os.getenv("MAX_SIMILAR_CHUNKS", "5"))

# Graph Storage Settings
GRAPH_STORAGE_TYPE = os.getenv("GRAPH_STORAGE_TYPE", "file")  # file, neo4j, memory
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Performance Settings
ENABLE_GRAPH_CACHING = os.getenv("ENABLE_GRAPH_CACHING", "true").lower() == "true"
GRAPH_CACHE_TTL = int(os.getenv("GRAPH_CACHE_TTL", "3600"))  # seconds

# Logging Settings
GRAPH_LOG_LEVEL = os.getenv("GRAPH_LOG_LEVEL", "INFO")
GRAPH_LOG_FILE = os.getenv("GRAPH_LOG_FILE", "./logs/graph.log")

def get_graph_config() -> dict:
    """
    Get complete graph configuration
    
    Returns:
        Dictionary with all graph configuration settings
    """
    return {
        "output_dir": GRAPH_OUTPUT_DIR,
        "cache_dir": GRAPH_CACHE_DIR,
        "api_key": RAG_ANYTHING_API_KEY,
        "base_url": RAG_ANYTHING_BASE_URL,
        "model": OLLAMA_MODEL,
        "max_chunks_per_batch": MAX_CHUNKS_PER_BATCH,
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "max_similar_chunks": MAX_SIMILAR_CHUNKS,
        "storage_type": GRAPH_STORAGE_TYPE,
        "neo4j": {
            "uri": NEO4J_URI,
            "username": NEO4J_USERNAME,
            "password": NEO4J_PASSWORD
        },
        "caching": {
            "enabled": ENABLE_GRAPH_CACHING,
            "ttl": GRAPH_CACHE_TTL
        },
        "logging": {
            "level": GRAPH_LOG_LEVEL,
            "file": GRAPH_LOG_FILE
        }
    }
