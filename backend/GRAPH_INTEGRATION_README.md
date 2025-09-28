# Graph Database Integration with RAG-Anything

This module integrates [RAG-Anything](https://github.com/HKUDS/RAG-Anything) with your existing ChromaDB setup to create a graph database that enhances your RAG system with relationship-aware retrieval.

## Features

- 🔗 **Graph-based Relationships**: Creates connections between chunks based on content similarity and document structure
- 📊 **Multi-modal Support**: Handles text, images, tables, and other content types from RAG-Anything
- 🚀 **ChromaDB Integration**: Leverages your existing ChromaDB chunks for graph construction
- 🔍 **Enhanced Querying**: Query both vector similarity and graph relationships
- 📈 **Statistics & Analytics**: Get insights into your knowledge graph structure
- 🔄 **Automatic Updates**: Graph automatically updates when new documents are uploaded
- 🔄 **Incremental Updates**: Add new chunks and update the graph dynamically

## Architecture

```
ChromaDB Chunks → Graph Nodes → Graph Edges → Enhanced RAG
     ↓              ↓            ↓              ↓
  Vector Store   Content      Relationships   Better Results
```

## Installation

1. **Install Dependencies**:
   ```bash
   pip install raganything[all] networkx neo4j
   ```

2. **Set Environment Variables**:
   ```bash
   export OLLAMA_BASE_URL="http://localhost:11434"
   export OLLAMA_MODEL="llama2"
   export GRAPH_OUTPUT_DIR="./graph_output"
   ```

## Usage

### 1. Building a Graph

```python
from app.GraphDB.graph_integration import build_domain_graph

# Build graph for entire domain
result = await build_domain_graph(domain_id=1, ollama_url="http://localhost:11434", model="llama2")

# Build graph for specific document
from app.GraphDB.graph_integration import GraphRAGIntegration
graph_integration = GraphRAGIntegration(ollama_url="http://localhost:11434", model="llama2")
result = await graph_integration.build_graph_from_chunks(
    domain_id=1,
    doc_id=123  # Optional: specific document
)
```

### 2. Querying the Graph

```python
from app.GraphDB.graph_integration import query_domain_graph

# Query the graph
results = await query_domain_graph(
    query="What are the main concepts?",
    domain_id=1,
    ollama_url="http://localhost:11434",
    model="llama2"
)

print(f"Found {results['total_found']} related chunks")
for result in results['results']:
    print(f"- {result['content'][:100]}...")
```

### 3. API Endpoints

The integration provides REST API endpoints:

- `POST /graph/build/{domain_id}` - Build graph for a domain
- `POST /graph/update/{domain_id}` - Update graph with new chunks
- `GET /graph/query/{domain_id}` - Query the graph
- `GET /graph/stats/{domain_id}` - Get graph statistics
- `POST /graph/rebuild/{domain_id}` - Rebuild the graph
- `GET /graph/health` - Health check

### 4. Example API Usage

```bash
# Build graph
curl -X POST "http://localhost:8000/graph/build/1" \
  -H "Authorization: Bearer your_token"

# Update graph with new chunks
curl -X POST "http://localhost:8000/graph/update/1" \
  -H "Authorization: Bearer your_token"

# Query graph
curl -X GET "http://localhost:8000/graph/query/1?query=main%20concepts" \
  -H "Authorization: Bearer your_token"

# Get statistics
curl -X GET "http://localhost:8000/graph/stats/1" \
  -H "Authorization: Bearer your_token"
```

## Graph Structure

### Nodes
Each chunk becomes a graph node with:
- `chunk_id`: Original chunk ID from database
- `content`: Chunk content
- `doc_id`: Document ID
- `user_id`: User ID
- `domain_id`: Domain ID
- `metadata`: Additional metadata
- `node_type`: Type of node (e.g., "chunk")

### Edges
Relationships between chunks:
- **Similarity Edges**: Based on ChromaDB vector similarity
- **Sequential Edges**: Chunks from the same document in order
- **Document Edges**: Chunks from related documents

## Configuration

Create a `.env` file with:

```bash
# Required
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Optional
GRAPH_OUTPUT_DIR=./graph_output
GRAPH_CACHE_DIR=./graph_cache
MAX_CHUNKS_PER_BATCH=1000
SIMILARITY_THRESHOLD=0.7
MAX_SIMILAR_CHUNKS=5
ENABLE_GRAPH_CACHING=true
GRAPH_CACHE_TTL=3600
```

## Testing

Run the test script to verify the integration:

```bash
cd backend
python test_graph_integration.py
```

## Graph Statistics

The system provides detailed statistics:

```python
stats = graph_integration.get_graph_statistics()
print(f"Nodes: {stats['total_nodes']}")
print(f"Edges: {stats['total_edges']}")
print(f"Node types: {stats['node_types']}")
print(f"Edge types: {stats['edge_types']}")
print(f"Connected components: {stats['connected_components']}")
```

## Performance Considerations

- **Batch Processing**: Process chunks in batches to manage memory
- **Caching**: Enable graph caching for better performance
- **Incremental Updates**: Only rebuild when necessary
- **Similarity Threshold**: Adjust based on your content type

## Troubleshooting

### Common Issues

1. **Ollama Server Not Available**:
   ```bash
   # Start Ollama server
   ollama serve
   
   # Check available models
   ollama list
   
   # Pull a model if needed
   ollama pull llama2
   ```

2. **No Chunks Found**:
   - Verify chunks exist in database
   - Check domain_id parameter
   - Ensure proper database connection

3. **Graph Building Fails**:
   - Check Ollama server is running
   - Verify model is available (`ollama list`)
   - Check output directory permissions
   - Verify network connectivity to Ollama server

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Integration with Existing System

The graph integration works alongside your existing:

- **ChromaDB**: Uses existing vector store for similarity
- **Database**: Reads from existing chunks table
- **Authentication**: Respects user permissions and domain access
- **API**: Integrates with existing FastAPI routes
- **Document Upload**: Automatically updates graph when new documents are uploaded via docling MCP

## Future Enhancements

- [ ] Neo4j integration for large-scale graphs
- [ ] Real-time graph updates
- [ ] Advanced graph algorithms (PageRank, community detection)
- [ ] Graph visualization interface
- [ ] Multi-language support
- [ ] Custom relationship types

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This integration follows the same license as the main project.

## Support

For issues and questions:
- Check the [RAG-Anything documentation](https://github.com/HKUDS/RAG-Anything)
- Review the test script for examples
- Check the API health endpoint: `GET /graph/health`
