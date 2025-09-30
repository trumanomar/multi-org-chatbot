"""
Example: Using Graph Database Integration
Demonstrates how to use RAG-Anything with your existing ChromaDB chunks
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the graph integration
from app.GraphDB.graph_integration import GraphRAGIntegration, build_domain_graph, query_domain_graph

async def example_usage():
    """
    Example of how to use the graph database integration
    """
    print("🔗 Graph Database Integration Example")
    print("=" * 50)
    
    # Get Ollama configuration from environment
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama2")
    
    print(f"✅ Ollama URL: {ollama_url}")
    print(f"✅ Ollama Model: {ollama_model}")
    
    # Test Ollama connection
    import requests
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [model["name"] for model in models]
            print(f"✅ Ollama server available")
            print(f"✅ Available models: {model_names}")
            
            if ollama_model not in model_names:
                print(f"⚠️  Model '{ollama_model}' not found. Available models: {model_names}")
                if model_names:
                    ollama_model = model_names[0].split(':')[0]
                    print(f"✅ Using model: {ollama_model}")
        else:
            print(f"❌ Ollama server responded with status {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Ollama server not available: {e}")
        return
    
    # Example 1: Build graph for a domain
    print("\n1️⃣ Building Graph for Domain")
    print("-" * 30)
    
    domain_id = 1  # Replace with your domain ID
    result = await build_domain_graph(domain_id, ollama_url, ollama_model)
    
    if result["status"] == "success":
        print(f"✅ Graph built successfully!")
        print(f"   📊 Processed {result['chunks_processed']} chunks")
        print(f"   🔗 Created {result['nodes_created']} nodes")
        print(f"   ➡️  Created {result['edges_created']} edges")
        print(f"   💾 Saved to: {result['graph_file']}")
    else:
        print(f"❌ Failed to build graph: {result['message']}")
        return
    
    # Example 2: Query the graph
    print("\n2️⃣ Querying the Graph")
    print("-" * 30)
    
    queries = [
        "What are the main topics discussed?",
        "Summarize the key concepts",
        "What are the important relationships?"
    ]
    
    for query in queries:
        print(f"\n🔍 Query: '{query}'")
        query_result = await query_domain_graph(query, domain_id, ollama_url, ollama_model)
        
        if query_result["status"] == "success":
            print(f"   ✅ Found {query_result['total_found']} results")
            
            # Show first few results
            for i, result in enumerate(query_result["results"][:2]):
                print(f"   📄 Result {i+1}:")
                print(f"      Content: {result['content'][:100]}...")
                print(f"      Document: {result['doc_name']}")
                if 'relationship' in result:
                    print(f"      Relationship: {result['relationship']}")
        else:
            print(f"   ❌ Query failed: {query_result['message']}")
    
    # Example 3: Advanced usage with GraphRAGIntegration class
    print("\n3️⃣ Advanced Usage")
    print("-" * 30)
    
    # Create integration instance
    graph_integration = GraphRAGIntegration(ollama_url=ollama_url, model=ollama_model)
    
    # Build graph with specific parameters
    result = await graph_integration.build_graph_from_chunks(
        domain_id=domain_id,
        doc_id=None,  # All documents in domain
        user_id=None  # All users
    )
    
    if result["status"] == "success":
        # Get graph statistics
        stats = graph_integration.get_graph_statistics()
        print("📈 Graph Statistics:")
        print(f"   🔢 Total nodes: {stats['total_nodes']}")
        print(f"   🔗 Total edges: {stats['total_edges']}")
        print(f"   📊 Node types: {stats['node_types']}")
        print(f"   🔀 Edge types: {stats['edge_types']}")
        print(f"   🧩 Connected components: {stats['connected_components']}")
        
        # Query with custom parameters
        custom_query_result = await graph_integration.query_graph(
            query="What are the main themes?",
            domain_id=domain_id,
            max_results=5
        )
        
        if custom_query_result["status"] == "success":
            print(f"\n🎯 Custom Query Results:")
            print(f"   Found {custom_query_result['total_found']} related chunks")
            
            for i, result in enumerate(custom_query_result["results"][:3]):
                print(f"   {i+1}. {result['content'][:80]}...")

        # Your requested query
        print("\n🧭 Doctors connected to hospitals (domain 3)")
        result = await graph_integration.query_graph(
            query="doctors hospitals",
            domain_id=3,
            max_results=10
        )
        print(result)
    
    print("\n🎉 Example completed successfully!")

async def example_api_usage():
    """
    Example of using the API endpoints
    """
    print("\n🌐 API Usage Example")
    print("=" * 30)
    
    print("""
    You can also use the REST API endpoints:
    
    1. Build Graph:
       POST /graph/build/{domain_id}
       Headers: Authorization: Bearer <token>
    
    2. Query Graph:
       GET /graph/query/{domain_id}?query=your_query&max_results=10
       Headers: Authorization: Bearer <token>
    
    3. Get Statistics:
       GET /graph/stats/{domain_id}
       Headers: Authorization: Bearer <token>
    
    4. Rebuild Graph:
       POST /graph/rebuild/{domain_id}
       Headers: Authorization: Bearer <token>
    
    5. Health Check:
       GET /graph/health
    """)

def main():
    """
    Main function to run examples
    """
    print("🚀 RAG-Anything Graph Integration Examples")
    print("=" * 60)
    
    # Run the async examples
    asyncio.run(example_usage())
    asyncio.run(example_api_usage())
    
    print("\n📚 For more information, see:")
    print("   - GRAPH_INTEGRATION_README.md")
    print("   - test_graph_integration.py")
    print("   - app/GraphDB/graph_integration.py")

if __name__ == "__main__":
    main()
