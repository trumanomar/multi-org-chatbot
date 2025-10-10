#!/usr/bin/env python3
"""
Test script for graph visualization endpoint
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.GraphDB.graph_integration import GraphRAGIntegration
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_graph_visualization():
    """Test the graph visualization functionality"""
    
    print("Testing Graph Visualization Integration")
    print("=" * 50)
    
    # Initialize graph integration
    graph_integration = GraphRAGIntegration()
    
    # Test domain ID - using domain 3 (you can change this to 5 or 7 if needed)
    domain_id = 3
    
    try:
        # Try to load existing graph
        print(f"Loading existing graph for domain {domain_id}...")
        loaded = await graph_integration.load_existing_graph(domain_id)
        
        if not loaded:
            print(f"No existing graph found for domain {domain_id}")
            print("Building graph from chunks...")
            build_result = await graph_integration.build_graph_from_chunks(
                domain_id=domain_id,
                extract_triplets=True
            )
            
            if build_result["status"] != "success":
                print(f"Failed to build graph: {build_result}")
                return False
            
            print(f"Graph built successfully: {build_result}")
        else:
            print(f"Graph loaded successfully")
        
        # Get graph statistics
        stats = graph_integration.get_graph_statistics()
        print(f"Graph Statistics:")
        print(f"   - Total Nodes: {stats['total_nodes']}")
        print(f"   - Total Edges: {stats['total_edges']}")
        print(f"   - Node Types: {stats['node_types']}")
        print(f"   - Edge Types: {stats['edge_types']}")
        print(f"   - Connected Components: {stats['connected_components']}")
        
        # Test graph visualization
        print(f"\nTesting graph visualization...")
        viz_result = graph_integration.draw_graph(
            file_path=f"./graph_output/test_graph_domain_{domain_id}.png",
            layout="spring",
            node_size=300,
            font_size=8
        )
        
        if viz_result["status"] == "success":
            print(f"Graph visualization generated successfully!")
            print(f"   - Image path: {viz_result['path']}")
            print(f"   - Nodes: {viz_result['nodes']}")
            print(f"   - Edges: {viz_result['edges']}")
        else:
            print(f"Failed to generate visualization: {viz_result}")
            return False
        
        # Test graph query
        print(f"\nTesting graph query...")
        query_result = await graph_integration.query_graph(
            query="test query",
            domain_id=domain_id,
            max_results=5
        )
        
        if query_result["status"] == "success":
            print(f"Graph query successful!")
            print(f"   - Results found: {query_result['total_found']}")
            print(f"   - Results returned: {len(query_result['results'])}")
        else:
            print(f"Graph query failed: {query_result}")
            return False
        
        print(f"\nAll tests passed!")
        return True
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    success = await test_graph_visualization()
    
    if success:
        print("\nGraph visualization integration test completed successfully!")
        print("\nNext steps:")
        print("1. Start the backend server")
        print("2. Test the /graph/visualize/{domain_id} endpoint")
        print("3. Test the Flutter frontend integration")
        return 0
    else:
        print("\nGraph visualization integration test failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
