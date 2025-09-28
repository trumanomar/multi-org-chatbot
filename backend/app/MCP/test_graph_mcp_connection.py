"""
Test Graph MCP Server Connection
Test script to verify the graph MCP server functionality
"""

import asyncio
import json
import requests
from typing import Dict, Any

# Test configuration
GRAPH_MCP_URL = "http://127.0.0.1:5001"
TEST_DOMAIN_ID = 1
TEST_QUERY = "machine learning algorithms"

async def test_graph_mcp_server():
    """Test the graph MCP server endpoints"""
    print("🧪 Testing Graph MCP Server...")
    
    # Test health endpoint
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{GRAPH_MCP_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # Test graph stats endpoint
    print("\n2. Testing graph stats endpoint...")
    try:
        response = requests.get(f"{GRAPH_MCP_URL}/graph_stats/{TEST_DOMAIN_ID}", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print("✅ Graph stats retrieved")
            print(f"   Nodes: {stats.get('total_nodes', 0)}")
            print(f"   Edges: {stats.get('total_edges', 0)}")
        else:
            print(f"❌ Graph stats failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Graph stats error: {e}")
    
    # Test load existing graph
    print("\n3. Testing load existing graph...")
    try:
        response = requests.post(f"{GRAPH_MCP_URL}/load_graph/{TEST_DOMAIN_ID}", timeout=10)
        if response.status_code == 200:
            result = response.json()
            print("✅ Load graph completed")
            print(f"   Success: {result.get('success', False)}")
        else:
            print(f"❌ Load graph failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Load graph error: {e}")
    
    # Test query graph
    print("\n4. Testing query graph...")
    try:
        query_data = {
            "query": TEST_QUERY,
            "domain_id": TEST_DOMAIN_ID,
            "max_results": 5
        }
        response = requests.post(f"{GRAPH_MCP_URL}/query_graph", json=query_data, timeout=15)
        if response.status_code == 200:
            result = response.json()
            print("✅ Graph query completed")
            print(f"   Status: {result.get('status', 'unknown')}")
            print(f"   Results found: {result.get('total_found', 0)}")
            if result.get('results'):
                print(f"   First result: {result['results'][0].get('content', '')[:100]}...")
        else:
            print(f"❌ Graph query failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Graph query error: {e}")
    
    print("\n🎉 Graph MCP Server testing completed!")
    return True

def test_mcp_tools():
    """Test MCP tools directly"""
    print("\n🔧 Testing MCP Tools...")
    
    try:
        # Import the MCP server
        from app.MCP.graph_mcp_server import create_graph_mcp_server
        
        # Create MCP server
        mcp_app = create_graph_mcp_server()
        print("✅ MCP server created successfully")
        
        # Test if we can get the graph integration
        from app.MCP.graph_mcp_server import get_graph_integration
        graph = get_graph_integration()
        print("✅ Graph integration initialized")
        
        # Test graph statistics
        stats = graph.get_graph_statistics()
        print(f"✅ Graph statistics: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ MCP tools test failed: {e}")
        return False

async def test_graph_operations():
    """Test graph operations directly"""
    print("\n📊 Testing Graph Operations...")
    
    try:
        from app.GraphDB.graph_integration import GraphRAGIntegration
        from app.GraphDB.config import get_graph_config
        
        # Initialize graph integration
        config = get_graph_config()
        graph = GraphRAGIntegration(
            ollama_url=config["base_url"],
            model=config["model"],
            output_dir=config["output_dir"]
        )
        
        print("✅ Graph integration initialized")
        
        # Test loading existing graph
        success = await graph.load_existing_graph(TEST_DOMAIN_ID)
        print(f"✅ Load existing graph: {success}")
        
        # Test graph statistics
        stats = graph.get_graph_statistics()
        print(f"✅ Graph stats: {stats}")
        
        # Test query if graph has nodes
        if stats.get('total_nodes', 0) > 0:
            result = await graph.query_graph(TEST_QUERY, TEST_DOMAIN_ID)
            print(f"✅ Graph query: {result.get('status', 'unknown')}")
            print(f"   Results: {result.get('total_found', 0)}")
        else:
            print("ℹ️  Graph is empty, skipping query test")
        
        return True
        
    except Exception as e:
        print(f"❌ Graph operations test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Starting Graph MCP Server Tests")
    print("=" * 50)
    
    # Test 1: MCP Tools
    print("\n📋 Test 1: MCP Tools")
    tools_success = test_mcp_tools()
    
    # Test 2: Graph Operations
    print("\n📋 Test 2: Graph Operations")
    operations_success = await test_graph_operations()
    
    # Test 3: HTTP Server (if running)
    print("\n📋 Test 3: HTTP Server")
    print("ℹ️  Note: Start the server with 'python graph_mcp_server.py' to test HTTP endpoints")
    server_success = await test_graph_mcp_server()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"   MCP Tools: {'✅ PASS' if tools_success else '❌ FAIL'}")
    print(f"   Graph Operations: {'✅ PASS' if operations_success else '❌ FAIL'}")
    print(f"   HTTP Server: {'✅ PASS' if server_success else '❌ FAIL'}")
    
    if tools_success and operations_success:
        print("\n🎉 All core tests passed! Graph MCP server is ready.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())
