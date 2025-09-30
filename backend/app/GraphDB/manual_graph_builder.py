"""
Manual Graph Builder
Use this to manually build the graph for your domain
"""

import asyncio
import sys
import os

# Add your project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def build_graph_manually(domain_id: int = 1, extract_triplets: bool = False):
    """
    Manually build graph for a domain
    
    Args:
        domain_id: Domain ID to build graph for
        extract_triplets: Whether to extract triplets (requires Ollama)
    """
    print("=" * 80)
    print(f"🏗️ MANUAL GRAPH BUILDER - Domain {domain_id}")
    print("=" * 80)
    print()
    
    try:
        from app.GraphDB.graph_integration import GraphRAGIntegration
        
        # Create graph integration instance
        graph = GraphRAGIntegration(
            ollama_url="http://localhost:11434",
            model="llama3.1:8b-instruct-q4_K_M",
            output_dir="./graph_output"
        )
        
        print(f"✅ Graph integration initialized")
        print(f"📁 Output directory: {graph.output_dir}")
        print()
        
        # Build the graph
        print(f"🔨 Building graph for domain {domain_id}...")
        print(f"   Extract triplets: {extract_triplets}")
        
        if not extract_triplets:
            print("   ⚠️ Triplet extraction disabled - graph will only have chunk nodes")
            print("   💡 Enable it by setting extract_triplets=True (requires Ollama)")
        
        print()
        print("⏳ This may take a while...")
        print()
        
        result = await graph.build_graph_from_chunks(
            domain_id=domain_id,
            extract_triplets=extract_triplets
        )
        
        print()
        print("=" * 80)
        print("📊 BUILD RESULTS:")
        print("=" * 80)
        print()
        
        if result["status"] == "success":
            print(f"✅ Status: {result['status']}")
            print(f"📄 Chunks processed: {result['chunks_processed']}")
            print(f"🔵 Nodes created: {result['nodes_created']}")
            print(f"🔗 Edges created: {result['edges_created']}")
            print(f"🧠 Triplets extracted: {result.get('triplets_extracted', 0)}")
            print(f"💾 Graph file: {result['graph_file']}")
            print()
            
            # Verify file exists
            if os.path.exists(result['graph_file']):
                size = os.path.getsize(result['graph_file'])
                print(f"✅ File verified: {result['graph_file']} ({size} bytes)")
            else:
                print(f"❌ Warning: File not found at {result['graph_file']}")
            
            # Get statistics
            stats = graph.get_graph_statistics()
            print()
            print("📈 Graph Statistics:")
            print(f"   Total nodes: {stats['total_nodes']}")
            print(f"   Total edges: {stats['total_edges']}")
            print(f"   Node types: {stats['node_types']}")
            print(f"   Edge types: {stats['edge_types']}")
            print(f"   Connected components: {stats['connected_components']}")
            
        elif result["status"] == "no_chunks":
            print(f"⚠️ Status: {result['status']}")
            print(f"Message: {result['message']}")
            print()
            print("💡 Make sure you have uploaded documents to this domain first!")
            
        else:
            print(f"❌ Status: {result['status']}")
            print(f"Error: {result.get('message', 'Unknown error')}")
        
        print()
        print("=" * 80)
        print("✅ GRAPH BUILDING COMPLETE")
        print("=" * 80)
        print()
        print("💡 Next steps:")
        print("   1. Test queries: python test_graph_query.py")
        print("   2. Use in your API: POST /graph/query/{domain_id}?query=your_query")
        print()
        
    except Exception as e:
        print(f"❌ Error building graph: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Configuration
    DOMAIN_ID = 1  # Change this to your domain ID
    EXTRACT_TRIPLETS = False  # Set to True if you want triplet extraction (requires Ollama)
    
    # Run
    asyncio.run(build_graph_manually(DOMAIN_ID, EXTRACT_TRIPLETS))