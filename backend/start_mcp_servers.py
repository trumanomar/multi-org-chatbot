"""
Start MCP Servers
Script to start both Docling MCP and Graph MCP servers
"""

import asyncio
import subprocess
import sys
import os
import time
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent / "app"))

def start_docling_mcp():
    """Start Docling MCP server"""
    print("🚀 Starting Docling MCP Server on port 5000...")
    try:
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "app.MCP.docling_mcp_server:fastapi_app",
            "--host", "127.0.0.1",
            "--port", "5000",
            "--reload"
        ], cwd=Path(__file__).parent)
        return process
    except Exception as e:
        print(f"❌ Failed to start Docling MCP server: {e}")
        return None

def start_graph_mcp():
    """Start Graph MCP server"""
    print("🚀 Starting Graph MCP Server on port 5001...")
    try:
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "app.MCP.graph_mcp_server:fastapi_app",
            "--host", "127.0.0.1",
            "--port", "5001",
            "--reload"
        ], cwd=Path(__file__).parent)
        return process
    except Exception as e:
        print(f"❌ Failed to start Graph MCP server: {e}")
        return None

def start_mysql_mcp():
    """Start MySQL MCP server"""
    print("🚀 Starting MySQL MCP Server on port 5002...")
    try:
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "app.MCP.mysql_mcp_server:fastapi_app",
            "--host", "127.0.0.1",
            "--port", "5002",
            "--reload"
        ], cwd=Path(__file__).parent)
        return process
    except Exception as e:
        print(f"❌ Failed to start MySQL MCP server: {e}")
        return None

def check_server_health(url: str, name: str, max_retries: int = 10) -> bool:
    """Check if server is healthy"""
    import requests
    
    for i in range(max_retries):
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ {name} server is healthy")
                return True
        except Exception:
            pass
        
        print(f"⏳ Waiting for {name} server... ({i+1}/{max_retries})")
        time.sleep(2)
    
    print(f"❌ {name} server failed health check")
    return False

async def main():
    """Main function to start all MCP servers"""
    print("🎯 Starting Multi-Org Chatbot MCP Servers")
    print("=" * 50)
    
    # Start Docling MCP server
    docling_process = start_docling_mcp()
    if not docling_process:
        print("❌ Failed to start Docling MCP server")
        return
    
    # Start Graph MCP server
    graph_process = start_graph_mcp()
    if not graph_process:
        print("❌ Failed to start Graph MCP server")
        if docling_process:
            docling_process.terminate()
        return
    
    # Start MySQL MCP server
    mysql_process = start_mysql_mcp()
    if not mysql_process:
        print("❌ Failed to start MySQL MCP server")
        if docling_process:
            docling_process.terminate()
        if graph_process:
            graph_process.terminate()
        return
    
    # Wait for servers to start
    print("\n⏳ Waiting for servers to start...")
    
    docling_healthy = check_server_health("http://127.0.0.1:5000", "Docling MCP")
    graph_healthy = check_server_health("http://127.0.0.1:5001", "Graph MCP")
    mysql_healthy = check_server_health("http://127.0.0.1:5002", "MySQL MCP")
    
    if docling_healthy and graph_healthy and mysql_healthy:
        print("\n🎉 All MCP servers are running successfully!")
        print("📋 Server Status:")
        print("   - Docling MCP: http://127.0.0.1:5000")
        print("   - Graph MCP: http://127.0.0.1:5001")
        print("   - MySQL MCP: http://127.0.0.1:5002")
        print("   - Main API: http://127.0.0.1:8000")
        print("\n💡 You can now start the main chatbot API server")
        print("   Run: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        
        try:
            # Keep servers running
            print("\n🔄 MCP servers are running. Press Ctrl+C to stop...")
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping MCP servers...")
            docling_process.terminate()
            graph_process.terminate()
            mysql_process.terminate()
            print("✅ MCP servers stopped")
    else:
        print("\n❌ Failed to start one or more MCP servers")
        if docling_process:
            docling_process.terminate()
        if graph_process:
            graph_process.terminate()
        if mysql_process:
            mysql_process.terminate()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
