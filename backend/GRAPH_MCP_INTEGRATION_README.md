# Graph MCP Integration with Multi-Org Chatbot

This document describes the integration of Graph MCP (Model Context Protocol) with the multi-org chatbot system, providing enhanced search capabilities through graph-based relationships.

## Overview

The system now includes two separate MCP servers:
1. **Docling MCP Server** (Port 5000) - Document processing and chunking
2. **Graph MCP Server** (Port 5001) - Graph database operations and relationship queries

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Main API      │    │   MCP Servers   │
│   (Flutter)     │◄──►│   (FastAPI)     │◄──►│                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Vector DB     │    │   Graph DB      │
                       │   (ChromaDB)    │    │   (NetworkX)    │
                       └─────────────────┘    └─────────────────┘
```

## Features

### 1. Document Upload Integration
When documents are uploaded:
1. **Docling MCP** processes and chunks the documents
2. **Vector Database** stores embeddings for similarity search
3. **Graph MCP** creates relationships between chunks
4. **Graph Database** stores node and edge information

### 2. Hybrid Search
Chat queries now use hybrid search combining:
- **Vector Search**: Semantic similarity using embeddings
- **Graph Search**: Relationship-based search through connected chunks
- **Combined Results**: Ranked and deduplicated results from both methods

### 3. Graph Operations
- **Build Graph**: Create graph from existing chunks
- **Query Graph**: Search through graph relationships
- **Update Graph**: Add new chunks to existing graph
- **Graph Stats**: Get statistics about graph structure

## File Structure

```
backend/
├── app/
│   ├── MCP/
│   │   ├── docling_mcp_server.py      # Docling MCP server
│   │   ├── graph_mcp_server.py        # Graph MCP server
│   │   ├── graph_mcp_client.py        # Graph MCP client
│   │   └── test_graph_mcp_connection.py
│   ├── GraphDB/
│   │   ├── graph_integration.py       # Graph database operations
│   │   └── config.py                  # Graph configuration
│   ├── Routes/
│   │   ├── ChatRoute.py               # Enhanced with hybrid search
│   │   └── Uploadroute.py             # Enhanced with graph integration
│   └── main.py                        # Main FastAPI application
├── start_mcp_servers.py               # Start both MCP servers
└── test_complete_integration.py       # Integration tests
```

## API Endpoints

### Chat Endpoints (Enhanced)
- `POST /chat/query` - Hybrid search with vector + graph
- `GET /chat/graph_health` - Check Graph MCP health
- `GET /chat/graph_stats/{domain_id}` - Get graph statistics
- `POST /chat/build_graph/{domain_id}` - Build graph for domain

### Upload Endpoints (Enhanced)
- `POST /admin/upload` - Upload with automatic graph integration
- `GET /admin/docling-health` - Check Docling MCP health

### Graph MCP Endpoints
- `GET /health` - Health check
- `POST /build_graph` - Build graph from chunks
- `POST /query_graph` - Query graph for information
- `POST /update_graph` - Update graph with new chunks
- `GET /graph_stats/{domain_id}` - Get graph statistics
- `POST /load_graph/{domain_id}` - Load existing graph

## Configuration

### Environment Variables
```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1

# Graph Configuration
GRAPH_OUTPUT_DIR=./graph_output
GRAPH_CACHE_DIR=./graph_cache
SIMILARITY_THRESHOLD=0.7
MAX_SIMILAR_CHUNKS=5

# MCP Server URLs
DOCLING_MCP_URL=http://127.0.0.1:5000
GRAPH_MCP_URL=http://127.0.0.1:5001
```

## Usage

### 1. Start MCP Servers
```bash
# Start both MCP servers
python start_mcp_servers.py

# Or start individually
# Docling MCP
python -m uvicorn app.MCP.docling_mcp_server:fastapi_app --host 127.0.0.1 --port 5000

# Graph MCP
python -m uvicorn app.MCP.graph_mcp_server:fastapi_app --host 127.0.0.1 --port 5001
```

### 2. Start Main API
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Test Integration
```bash
python test_complete_integration.py
```

## Workflow

### Document Upload Process
1. **Upload**: User uploads documents through admin interface
2. **Docling Processing**: Documents are processed and chunked by Docling MCP
3. **Vector Storage**: Chunks are stored in ChromaDB with embeddings
4. **Graph Creation**: Graph MCP creates relationships between chunks
5. **Graph Storage**: Graph structure is saved to JSON files

### Chat Query Process
1. **Query**: User asks a question
2. **Hybrid Search**: System performs both vector and graph search
3. **Result Combination**: Results are combined and ranked
4. **LLM Processing**: Combined context is sent to LLM
5. **Response**: Enhanced answer with graph relationships

## Graph Relationships

The system creates several types of relationships:

### 1. Similarity Relationships
- **Edge Type**: `similarity`
- **Weight**: 0.8 (high relevance)
- **Description**: Chunks with similar content

### 2. Sequential Relationships
- **Edge Type**: `sequential`
- **Weight**: 1.0 (highest relevance)
- **Description**: Chunks from the same document in order

### 3. Document Relationships
- **Edge Type**: `document`
- **Weight**: 0.9
- **Description**: Chunks from the same document

## Benefits

### 1. Enhanced Search Quality
- **Semantic Search**: Vector embeddings for meaning-based search
- **Relationship Search**: Graph traversal for context-aware results
- **Combined Intelligence**: Best of both approaches

### 2. Better Context Understanding
- **Connected Information**: Find related chunks through graph relationships
- **Context Preservation**: Maintain document structure and flow
- **Cross-Reference Discovery**: Find connections between different documents

### 3. Improved User Experience
- **More Relevant Results**: Hybrid search provides better answers
- **Contextual Information**: Related information is automatically included
- **Comprehensive Coverage**: Both direct and indirect relationships are explored

## Troubleshooting

### Common Issues

1. **MCP Servers Not Running**
   ```bash
   # Check if servers are running
   curl http://127.0.0.1:5000/health
   curl http://127.0.0.1:5001/health
   ```

2. **Graph Not Building**
   - Check if documents are uploaded and chunked
   - Verify domain_id is correct
   - Check graph output directory permissions

3. **Hybrid Search Not Working**
   - Ensure both MCP servers are running
   - Check network connectivity between services
   - Verify authentication tokens

### Debug Commands

```bash
# Check MCP server health
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:5001/health

# Check graph stats
curl http://127.0.0.1:5001/graph_stats/1

# Test graph query
curl -X POST http://127.0.0.1:5001/query_graph \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "domain_id": 1, "max_results": 5}'
```

## Future Enhancements

1. **Neo4j Integration**: Replace file-based storage with Neo4j
2. **Real-time Updates**: Live graph updates as documents are processed
3. **Advanced Analytics**: Graph analytics and insights
4. **Visualization**: Graph visualization for administrators
5. **Performance Optimization**: Caching and indexing improvements

## Support

For issues or questions:
1. Check the logs in the console output
2. Run the integration test: `python test_complete_integration.py`
3. Verify all services are running and healthy
4. Check the configuration and environment variables
