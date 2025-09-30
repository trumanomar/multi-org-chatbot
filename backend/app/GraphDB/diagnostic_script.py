"""
Graph Diagnostic Script
Run this to check if your graph is working properly
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# Add your project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def diagnostic():
    print("=" * 80)
    print("🔍 GRAPH DIAGNOSTIC TOOL")
    print("=" * 80)
    print()
    
    # 1. Check output directory
    print("1️⃣ Checking output directory...")
    output_dir = "./graph_output"
    if os.path.exists(output_dir):
        print(f"   ✅ Output directory exists: {output_dir}")
        files = os.listdir(output_dir)
        print(f"   📁 Files in directory: {files}")
    else:
        print(f"   ❌ Output directory doesn't exist: {output_dir}")
        print(f"   Creating it now...")
        os.makedirs(output_dir, exist_ok=True)
        print(f"   ✅ Created: {output_dir}")
    print()
    
    # 2. Check if graph files exist
    print("2️⃣ Checking for existing graph files...")
    graph_files = [f for f in os.listdir(output_dir) if f.startswith("graph_domain_") and f.endswith(".json")]
    if graph_files:
        print(f"   ✅ Found {len(graph_files)} graph file(s):")
        for f in graph_files:
            file_path = os.path.join(output_dir, f)
            size = os.path.getsize(file_path)
            print(f"      - {f} ({size} bytes)")
            
            # Check content
            try:
                with open(file_path, 'r') as fp:
                    data = json.load(fp)
                    print(f"        Nodes: {len(data.get('nodes', []))}, Edges: {len(data.get('edges', []))}")
            except Exception as e:
                print(f"        ❌ Error reading file: {e}")
    else:
        print("   ⚠️ No graph files found")
    print()
    
    # 3. Check database connection
    print("3️⃣ Checking database connection...")
    try:
        from app.DB.db import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        result = db.execute(text("SELECT COUNT(*) FROM chunks"))
        chunk_count = result.scalar()
        print(f"   ✅ Database connected")
        print(f"   📊 Total chunks in database: {chunk_count}")
        
        # Check chunks by domain
        result = db.execute(text("SELECT domain_id, COUNT(*) as count FROM chunks GROUP BY domain_id"))
        for row in result:
            print(f"      Domain {row.domain_id}: {row.count} chunks")
        
        db.close()
    except Exception as e:
        print(f"   ❌ Database connection error: {e}")
    print()
    
    # 4. Check Ollama service
    print("4️⃣ Checking Ollama service...")
    try:
        import requests
        ollama_url = "http://localhost:11434"
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"   ✅ Ollama is running at {ollama_url}")
            print(f"   📦 Available models: {[m['name'] for m in models]}")
        else:
            print(f"   ❌ Ollama returned status code: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Cannot connect to Ollama: {e}")
        print(f"   ⚠️ Triplet extraction will not work without Ollama")
    print()
    
    # 5. Check Graph MCP Server
    print("5️⃣ Checking Graph MCP Server...")
    try:
        import requests
        mcp_url = "http://127.0.0.1:5001"
        response = requests.get(f"{mcp_url}/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"   ✅ Graph MCP Server is running")
            print(f"   Status: {health}")
        else:
            print(f"   ❌ Graph MCP returned status code: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Cannot connect to Graph MCP: {e}")
        print(f"   💡 Start it with: python graph_mcp_server.py")
    print()
    
    # 6. Test graph operations
    print("6️⃣ Testing graph operations...")
    try:
        from app.GraphDB.graph_integration import GraphRAGIntegration
        
        # Create instance
        graph = GraphRAGIntegration(
            ollama_url="http://localhost:11434",
            model="llama3.1:8b-instruct-q4_K_M",
            output_dir="./graph_output"
        )
        print("   ✅ GraphRAGIntegration initialized")
        
        # Try to load graph for domain 1
        domain_id = 1
        loaded = await graph.load_existing_graph(domain_id)
        
        if loaded:
            print(f"   ✅ Loaded graph for domain {domain_id}")
            print(f"      Nodes: {graph.graph.number_of_nodes()}")
            print(f"      Edges: {graph.graph.number_of_edges()}")
            
            # Get stats
            stats = graph.get_graph_statistics()
            print(f"   📊 Graph statistics:")
            print(f"      Node types: {stats['node_types']}")
            print(f"      Edge types: {stats['edge_types']}")
            
            # Test query
            print("   🔍 Testing query...")
            query_result = await graph.query_graph("test", domain_id, max_results=5)
            print(f"      Query status: {query_result['status']}")
            print(f"      Results found: {query_result.get('total_found', 0)}")
            
        else:
            print(f"   ⚠️ No graph found for domain {domain_id}")
            print(f"   💡 You need to:")
            print(f"      1. Upload documents")
            print(f"      2. Wait for graph to be built")
            print(f"      OR")
            print(f"      Manually build with: await graph.build_graph_from_chunks(domain_id=1)")
            
    except Exception as e:
        print(f"   ❌ Error testing graph operations: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # 7. Recommendations
    print("=" * 80)
    print("💡 RECOMMENDATIONS:")
    print("=" * 80)
    print()
    
    if not graph_files:
        print("⚠️ No graph files found!")
        print("   Steps to create a graph:")
        print("   1. Make sure Graph MCP server is running: python graph_mcp_server.py")
        print("   2. Upload documents through your API")
        print("   3. The graph will be automatically created")
        print("   OR")
        print("   Manually trigger: POST /admin/update-graph/{doc_id}")
        print()
    
    print("✅ Diagnostic complete!")
    print()

if __name__ == "__main__":
    asyncio.run(diagnostic())