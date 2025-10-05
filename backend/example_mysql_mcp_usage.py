"""
Example MySQL MCP Usage
Demonstrates how other MCPs can integrate with the MySQL MCP server
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent / "app"))

from app.MCP.mysql_mcp_client import MySQLMCPClient, DoclingMySQLIntegration, GraphMySQLIntegration

async def example_docling_mysql_integration():
    """Example: How Docling MCP can use MySQL MCP"""
    print("📄 Docling → MySQL Integration Example")
    print("-" * 40)
    
    # Initialize the integration
    docling_integration = DoclingMySQLIntegration()
    
    # Simulate processed chunks from Docling
    processed_chunks = [
        {
            "content": "This is the first chunk of processed document content.",
            "metadata": {"page": 1, "section": "introduction", "confidence": 0.95}
        },
        {
            "content": "This is the second chunk with more detailed information.",
            "metadata": {"page": 2, "section": "main_content", "confidence": 0.88}
        },
        {
            "content": "Final chunk with conclusions and summary.",
            "metadata": {"page": 3, "section": "conclusion", "confidence": 0.92}
        }
    ]
    
    # Get a valid doc_id first
    client = MySQLMCPClient()
    doc_query = client.query("SELECT id, name FROM docs LIMIT 1")
    
    if not doc_query.get("success") or not doc_query["data"]:
        print("   ❌ No documents found in database")
        return
    
    doc_id = doc_query["data"][0]["id"]
    doc_name = doc_query["data"][0]["name"]
    print(f"   ✅ Using doc_id: {doc_id} (document: {doc_name})")
    
    # Store chunks in MySQL
    try:
        result = docling_integration.store_processed_chunks(doc_id=doc_id, chunks=processed_chunks)
        print(f"✅ Stored {result.get('inserted_chunks', 0)} chunks out of {result.get('total_chunks', 0)}")
    
        # Query the stored chunks
        chunks_query = client.query(
            "SELECT id, content, meta_data FROM chunks WHERE doc_id = :doc_id ORDER BY id DESC LIMIT 3",
            {"doc_id": doc_id}
        )
        
        if chunks_query.get("success"):
            print("📋 Latest stored chunks:")
            for chunk in chunks_query["data"]:
                print(f"   - Chunk {chunk['id']}: {chunk['content'][:50]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def example_graph_mysql_integration():
    """Example: How Graph MCP can use MySQL MCP"""
    print("\n🕸️ Graph → MySQL Integration Example")
    print("-" * 40)
    
    # Initialize the integration
    graph_integration = GraphMySQLIntegration()
    
    # Get chunks for graph building
    try:
        chunks = graph_integration.get_chunks_for_graph_building(domain_id=1)
        print(f"✅ Retrieved {len(chunks)} chunks for graph building")
        
        if chunks:
            print("📋 Sample chunks for graph:")
            for i, chunk in enumerate(chunks[:3]):
                print(f"   {i+1}. {chunk['content'][:60]}...")
                print(f"      - Document: {chunk['doc_name']}")
                print(f"      - User: {chunk['username']}")
        
        # Simulate storing graph results in chat message
        # (This would typically happen after a chat interaction)
        mock_graph_results = {
            "related_chunks": [1, 2, 3],
            "graph_paths": [
                {"source": 1, "target": 2, "similarity": 0.85},
                {"source": 2, "target": 3, "similarity": 0.78}
            ],
            "central_nodes": [2],
            "confidence": 0.82
        }
        
        # Store graph results (assuming message_id=1 exists)
        store_result = graph_integration.store_graph_results(
            message_id=1, 
            graph_results=mock_graph_results
        )
        
        if store_result.get("success"):
            print(f"✅ Stored graph results for message {store_result.get('affected_rows', 0)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def example_direct_mysql_queries():
    """Example: Direct MySQL queries for analytics and reporting"""
    print("\n📊 Direct MySQL Queries Example")
    print("-" * 30)
    
    client = MySQLMCPClient()
    
    try:
        # 1. Domain Analytics
        print("1. Domain Analytics:")
        domain_stats = client.query("""
            SELECT 
                d.name as domain_name,
                COUNT(DISTINCT u.id) as user_count,
                COUNT(DISTINCT doc.id) as doc_count,
                COUNT(DISTINCT c.id) as chunk_count
            FROM domains d
            LEFT JOIN users u ON d.id = u.domain_id
            LEFT JOIN docs doc ON d.id = doc.domain_id
            LEFT JOIN chunks c ON d.id = c.domain_id
            GROUP BY d.id, d.name
            ORDER BY user_count DESC
        """)
        
        if domain_stats.get("success"):
            for domain in domain_stats["data"]:
                print(f"   - {domain['domain_name']}: {domain['user_count']} users, "
                      f"{domain['doc_count']} docs, {domain['chunk_count']} chunks")
        
        # 2. User Activity
        print("\n2. Recent User Activity:")
        user_activity = client.query("""
            SELECT 
                u.username,
                d.name as domain_name,
                COUNT(cm.id) as message_count,
                MAX(cm.created_at) as last_activity
            FROM users u
            JOIN domains d ON u.domain_id = d.id
            LEFT JOIN chat_messages cm ON u.id = cm.user_id
            WHERE cm.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY u.id, u.username, d.name
            ORDER BY message_count DESC
            LIMIT 5
        """)
        
        if user_activity.get("success"):
            for user in user_activity["data"]:
                print(f"   - {user['username']} ({user['domain_name']}): "
                      f"{user['message_count']} messages, last: {user['last_activity']}")
        
        # 3. Content Statistics
        print("\n3. Content Statistics:")
        content_stats = client.query("""
            SELECT 
                AVG(LENGTH(content)) as avg_chunk_length,
                MAX(LENGTH(content)) as max_chunk_length,
                MIN(LENGTH(content)) as min_chunk_length,
                COUNT(*) as total_chunks
            FROM chunks
        """)
        
        if content_stats.get("success") and content_stats["data"]:
            stats = content_stats["data"][0]
            avg_length = float(stats['avg_chunk_length']) if stats['avg_chunk_length'] else 0
            print(f"   - Average chunk length: {avg_length:.0f} characters")
            print(f"   - Max chunk length: {stats['max_chunk_length']} characters")
            print(f"   - Min chunk length: {stats['min_chunk_length']} characters")
            print(f"   - Total chunks: {stats['total_chunks']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def example_crud_operations():
    """Example: CRUD operations using MySQL MCP"""
    print("\n🔄 CRUD Operations Example")
    print("-" * 30)
    
    client = MySQLMCPClient()
    
    try:
        # First, get a valid user_id and domain_id
        print("1. Getting valid user and domain IDs:")
        user_query = client.query("SELECT id, username, domain_id FROM users LIMIT 1")
        
        if not user_query.get("success") or not user_query["data"]:
            print("   ❌ No users found in database")
            return
        
        user = user_query["data"][0]
        user_id = user["id"]
        domain_id = user["domain_id"]
        print(f"   ✅ Using user_id: {user_id} (username: {user['username']}), domain_id: {domain_id}")
        
        # CREATE - Insert new feedback
        print("\n2. Creating new feedback:")
        feedback_data = {
            "user_id": user_id,
            "domain_id": domain_id,
            "content": "The MySQL MCP integration is working great!",
            "rating": 5,
            "question": "How do you like the new MySQL MCP integration?"
        }
        
        insert_result = client.insert("feedback", feedback_data)
        if insert_result.get("success"):
            feedback_id = insert_result.get("last_insert_id")
            print(f"   ✅ Created feedback with ID: {feedback_id}")
            
            # READ - Query the inserted feedback
            print("\n3. Reading the feedback:")
            read_result = client.query(
                "SELECT * FROM feedback WHERE id = :id",
                {"id": feedback_id}
            )
            
            if read_result.get("success") and read_result["data"]:
                feedback = read_result["data"][0]
                print(f"   ✅ Found feedback: '{feedback['content']}' (Rating: {feedback['rating']})")
            
            # UPDATE - Modify the feedback
            print("\n4. Updating the feedback:")
            update_result = client.update(
                "feedback",
                {"rating": 4, "content": "Updated: The MySQL MCP integration is working well!"},
                "id = :id",
                {"id": feedback_id}
            )
            
            if update_result.get("success"):
                print(f"   ✅ Updated {update_result['affected_rows']} feedback record(s)")
                
                # Verify the update
                verify_result = client.query(
                    "SELECT rating, content FROM feedback WHERE id = :id",
                    {"id": feedback_id}
                )
                
                if verify_result.get("success") and verify_result["data"]:
                    updated = verify_result["data"][0]
                    print(f"   ✅ Verified update: Rating {updated['rating']}, Content: '{updated['content']}'")
            
            # DELETE - Clean up the test data
            print("\n5. Cleaning up test data:")
            print(f"   💡 Note: DELETE operations are not allowed through the query endpoint for security.")
            print(f"   🧹 Test feedback with ID {feedback_id} was created for demonstration purposes.")
            print(f"   💡 In a real application, you would use the update endpoint or direct database access for cleanup.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    """Run all examples"""
    print("🚀 MySQL MCP Usage Examples")
    print("=" * 50)
    
    # Check if MySQL MCP server is running
    client = MySQLMCPClient()
    try:
        health = client.health_check()
        print("✅ MySQL MCP server is running!")
    except Exception as e:
        print("❌ MySQL MCP server is not accessible")
        print(f"   Error: {e}")
        print("\n💡 Please start the MySQL MCP server first:")
        print("   python start_mcp_servers.py")
        return
    
    # Run examples
    await example_docling_mysql_integration()
    await example_graph_mysql_integration()
    await example_direct_mysql_queries()
    await example_crud_operations()
    
    print("\n🎉 All examples completed!")
    print("\n💡 These examples show how other MCPs can:")
    print("   - Store processed data in MySQL")
    print("   - Query data for analysis")
    print("   - Perform CRUD operations")
    print("   - Integrate with the RAG system")

if __name__ == "__main__":
    asyncio.run(main())
