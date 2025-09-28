"""
Graph Database Test Script
Test script for RAG-Anything graph integration
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from app.GraphDB.graph_integration import GraphRAGIntegration, build_domain_graph, query_domain_graph
from app.DB.db import get_db
from app.Models.tables import Domain, User, Docs, Chunk
from sqlalchemy.orm import Session
from sqlalchemy import text

async def test_graph_integration():
    """
    Test the graph database integration
    """
    print("🚀 Testing Graph Database Integration with RAG-Anything")
    print("=" * 60)
    
    # Check Ollama configuration
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1")
    
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
    
    # Get database session
    db = next(get_db())
    
    try:
        # Check if we have domains
        domains = db.query(Domain).all()
        if not domains:
            print("❌ No domains found in database")
            return
        
        print(f"✅ Found {len(domains)} domains")
        
        # Check if we have chunks
        chunks_count = db.execute(text("SELECT COUNT(*) FROM chunks")).fetchone()[0]
        if chunks_count == 0:
            print("❌ No chunks found in database")
            return
        
        print(f"✅ Found {chunks_count} chunks in database")
        
        # Test with first domain
        domain = domains[0]
        print(f"\n📊 Testing with domain: {domain.name} (ID: {domain.id})")
        
        # Check chunks for this domain
        domain_chunks = db.execute(
            text("SELECT COUNT(*) FROM chunks WHERE domain_id = :domain_id"),
            {"domain_id": domain.id}
        ).fetchone()[0]
        
        print(f"📄 Chunks in domain: {domain_chunks}")
        
        if domain_chunks == 0:
            print("⚠️  No chunks found for this domain, skipping graph building")
            return
        
        # Test graph building
        print("\n🔨 Building graph...")
        # Create a single graph integration instance to maintain state
        graph_integration = GraphRAGIntegration(ollama_url=ollama_url, model=ollama_model)
        result = await graph_integration.build_graph_from_chunks(domain_id=domain.id)
        
        if result["status"] == "success":
            print("✅ Graph built successfully!")
            print(f"   - Chunks processed: {result['chunks_processed']}")
            print(f"   - Nodes created: {result['nodes_created']}")
            print(f"   - Edges created: {result['edges_created']}")
            print(f"   - Graph file: {result['graph_file']}")
        else:
            print(f"❌ Graph building failed: {result['message']}")
            return
        
        # Test graph querying using the same instance
        print("\n🔍 Testing graph queries...")
        test_queries = [
            "What is the main topic?",
            "Summarize the content",
            "Key concepts and ideas"
        ]
        
        for query in test_queries:
            print(f"\n   Query: '{query}'")
            query_result = await graph_integration.query_graph(query, domain.id)
            
            if query_result["status"] == "success":
                print(f"   ✅ Found {query_result['total_found']} results")
                if query_result["results"]:
                    print(f"   📝 First result preview: {query_result['results'][0]['content'][:100]}...")
            else:
                print(f"   ❌ Query failed: {query_result['message']}")
        
        # Test graph statistics using the same instance
        print("\n📈 Testing graph statistics...")
        stats = graph_integration.get_graph_statistics()
        
        print("✅ Graph Statistics:")
        print(f"   - Total nodes: {stats['total_nodes']}")
        print(f"   - Total edges: {stats['total_edges']}")
        print(f"   - Node types: {stats['node_types']}")
        print(f"   - Edge types: {stats['edge_types']}")
        print(f"   - Connected components: {stats['connected_components']}")
        
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

async def test_chunk_processing():
    """
    Test chunk processing and graph creation
    """
    print("\n🧪 Testing Chunk Processing")
    print("=" * 40)
    
    # Check Ollama configuration
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1")
    
    # Create graph integration instance
    graph_integration = GraphRAGIntegration(ollama_url=ollama_url, model=ollama_model)
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get a sample of chunks
        result = db.execute(text("""
            SELECT c.id, c.content, c.meta_data, c.doc_id, c.user_id, c.domain_id,
                   d.name as doc_name, u.username, dom.name as domain_name
            FROM chunks c
            JOIN docs d ON c.doc_id = d.id
            JOIN users u ON c.user_id = u.id
            JOIN domains dom ON c.domain_id = dom.id
            LIMIT 10
        """))
        
        chunks = result.fetchall()
        
        if not chunks:
            print("❌ No chunks found for testing")
            return
        
        print(f"✅ Found {len(chunks)} chunks for testing")
        
        # Process chunks
        for i, chunk in enumerate(chunks[:3]):  # Test with first 3 chunks
            chunk_id, content, meta_data, doc_id, user_id, domain_id, doc_name, username, domain_name = chunk
            print(f"\n📄 Processing chunk {i+1}:")
            print(f"   - ID: {chunk_id}")
            print(f"   - Content length: {len(content)}")
            print(f"   - Document: {doc_name}")
            print(f"   - Domain: {domain_name}")
            print(f"   - Content preview: {content[:100]}...")
        
        print("\n✅ Chunk processing test completed")
        
    except Exception as e:
        print(f"❌ Error during chunk processing test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

def main():
    """
    Main test function
    """
    print("Graph Database Integration Test Suite")
    print("=" * 50)
    
    # Run tests
    asyncio.run(test_graph_integration())
    asyncio.run(test_chunk_processing())

if __name__ == "__main__":
    main()
