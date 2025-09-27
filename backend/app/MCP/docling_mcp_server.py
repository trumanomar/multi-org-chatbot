
from fastapi import FastAPI, HTTPException
from fastmcp import FastMCP
from pydantic import BaseModel
from app.utilis.utils import load_and_split
import asyncio
from threading import Thread

# FastAPI app for HTTP endpoints
fastapi_app = FastAPI(
    title="Docling API Server",
    description="Document processing API",
    version="1.0.0"
)

class SplitRequest(BaseModel):
    file_path: str
    chunk_size: int = 500
    chunk_overlap: int = 50

@fastapi_app.post("/load_and_split")
def load_and_split_http(req: SplitRequest):
    try:
        result = load_and_split(req.file_path, req.chunk_size, req.chunk_overlap)
        return {"success": True, "chunks": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.get("/health")
def health_check():
    return {"status": "healthy"}

# Separate MCP server
def create_mcp_server():
    mcp_app = FastAPI()
    mcp = FastMCP.from_fastapi(mcp_app, name="docling-mcp")
    
    @mcp.tool()
    def load_and_split_tool(file_path: str, chunk_size: int = 500, chunk_overlap: int = 50):
        return load_and_split(file_path, chunk_size, chunk_overlap)
    
    return mcp_app

# Run both servers
if __name__ == "__main__":
    import uvicorn
    
    # Run FastAPI server (this will have working docs)
    uvicorn.run(fastapi_app, host="127.0.0.1", port=5000)
    

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.utilis.utils import load_and_split

app = FastAPI(
    title="Docling Document Processor",
    description="API for loading and splitting documents into chunks",
    version="1.0.0"
)

class SplitRequest(BaseModel):
    file_path: str
    chunk_size: int = 500
    chunk_overlap: int = 50

class SplitResponse(BaseModel):
    success: bool
    chunks: list
    total_chunks: int
    message: str = None

@app.post("/load_and_split", response_model=SplitResponse)
def load_and_split_endpoint(req: SplitRequest):
    """
    Load a document and split it into chunks.
    
    This endpoint processes documents and returns them as manageable chunks
    for further processing or analysis.
    """
    try:
        chunks = load_and_split(req.file_path, req.chunk_size, req.chunk_overlap)
        return SplitResponse(
            success=True,
            chunks=chunks,
            total_chunks=len(chunks) if isinstance(chunks, list) else 0,
            message=f"Successfully processed {req.file_path}"
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.get("/")
def root():
    return {"message": "Docling Document Processor API", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "healthy", "service": "docling-processor"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000, reload=True)
