"""
Test Graph Query Script
Test if your graph queries are working properly
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_queries(domain_id: int = 1):
    """Test various graph queries"""
    
    print("=" * 80)
    print(f"🔍 TESTING GRAPH QUERIES - Domain {domain_id}")
    print("=" * 80)
    print()
    
    try:
        from app.GraphDB.graph_integration import GraphRAGIntegration
        
        # Initialize
        graph = GraphRAGIntegration(
            ollama_url="http://localhost:11434",
            model="llama3.1:8b-instruct-q4_K_M",
            output_dir="./graph_output"
        )
        
        print("1️⃣ Loading graph...")
        loaded = await graph.load_existing_graph(domain_id)
        
        if not loaded:
            print("   ❌ No graph found!")
            print(f"   💡 Build it first: python manual_graph_builder.py")
            return
        
        print(f"   ✅ Graph loaded successfully")
        print(f"   📊 Nodes: {graph.graph.number_of_nodes()}")
        print(f"   🔗 Edges: {graph.graph.number_of_edges()}")
        print()
        
        # Test queries
        test_queries_list = [
            "machine learning",
            "python",
            "data",
            "test",
        ]
        
        print("2️⃣ Testing queries...")
        print()
        
        for query in test_queries_list:
            print(f"   Query: '{query}'")
            
            # Test graph query
            result = await graph.query_graph(query, domain_id, max_results=5)
            
            if result['status'] == 'success':
                print(f"      ✅ Graph results: {result['total_found']}")
                if result['total_found'] > 0:
                    print(f"         First result: {result['results'][0].get('content', '')[:100]}...")
            else:
                print(f"      ❌ Error: {result.get('message')}")
            
            print()
        
        print("=" * 80)
        print("3️⃣ Testing Combined Query (Vector + Graph)...")
        print("=" * 80)
        print()
        
        combined_result = await graph.query_separate("machine learning", domain_id, k=5)
        
        print(f"Vector DB results: {combined_result['vector_total']}")
        print(f"Graph results: {combined_result['graph_total']}")
        print()
        
        if combined_result['vector_total'] > 0:
            print("✅ Vector DB is working")
        else:
            print("⚠️ Vector DB returned 0 results")
        
        if combined_result['graph_total'] > 0:
            print("✅ Graph DB is working")
        else:
            print("⚠️ Graph DB returned 0 results")
            print()
            print("💡 Possible reasons:")
            print("   1. Graph is empty (no nodes)")
            print("   2. Query doesn't match any content")
            print("   3. Graph file wasn't loaded properly")
            print()
            print("🔧 Try:")
            print("   1. Run diagnostic: python diagnostic_script.py")
            print("   2. Rebuild graph: python manual_graph_builder.py")
        
        print()
        print("✅ Testing complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    DOMAIN_ID = 1  # Change to your domain ID
    asyncio.run(test_queries(DOMAIN_ID))