# app/Routes/Uploadroute.py - Updated with Graph Integration
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import os, traceback, asyncio, psutil, gc
from tempfile import NamedTemporaryFile
from sqlalchemy.orm import Session
import json
from concurrent.futures import ThreadPoolExecutor

from app.VectorDB.DB import add_documents, persist
from app.DB.db import get_db
from app.Models.tables import User
from app.DB.save_docs import save_document
from app.DB.save_chunks import save_chunks
from app.auth.dependencies import require_admin, get_current_principal, Principal

from app.utilis.docling_client import DoclingHttpClient
from app.MCP.graph_mcp_client import GraphMCPClient  # Add this import
from langchain.docstore.document import Document

router = APIRouter(prefix="/admin", tags=["Admin"])
BATCH_SIZE = 100
ALLOWED_EXTS = {".pdf", ".docx", ".txt", ".csv", ".xlsx", ".md"}

# Configuration
GRAPH_MCP_URL = os.getenv("GRAPH_MCP_URL", "http://127.0.0.1:5001")
ENABLE_GRAPH_AUTO_UPDATE = os.getenv("ENABLE_GRAPH_AUTO_UPDATE", "true").lower() == "true"

@router.post("/upload", dependencies=[Depends(require_admin)])
async def upload_files(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    if principal.domain_id is None:
        raise HTTPException(status_code=403, detail="Domain missing in token")

    # Verify user
    db_user = db.query(User).filter(User.username == principal.sub).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="User not found in database")

    total_chunks = 0
    file_counts = []
    processed_doc_ids = []  # Track processed documents for graph update

    # Initialize docling client
    docling_client = DoclingHttpClient(base_url="http://127.0.0.1:5000")
    
    # Check if docling service is healthy
    if not await docling_client.health_check_async():
        raise HTTPException(
            status_code=503, 
            detail="Docling service is not available. Please ensure the MCP server is running."
        )
    
    # Initialize graph client (optional - won't fail if graph service is down)
    graph_client = None
    graph_available = False
    if ENABLE_GRAPH_AUTO_UPDATE:
        try:
            graph_client = GraphMCPClient(mcp_url=GRAPH_MCP_URL)
            health = await graph_client.health_check()
            graph_available = health.get("status") == "healthy"
            if graph_available:
                print(f"[upload] Graph MCP service available at {GRAPH_MCP_URL}")
            else:
                print(f"[upload] Graph MCP service not available, skipping graph updates")
        except Exception as e:
            print(f"[upload] Could not connect to Graph MCP service: {e}")
            graph_available = False
        
    for idx, file in enumerate(files):
        suffix = os.path.splitext(file.filename)[-1].lower()
        if suffix not in ALLOWED_EXTS:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type: {suffix}. Supported: {sorted(ALLOWED_EXTS)}",
            )

        print(f"[upload] Processing file {idx+1}/{len(files)}: {file.filename}")
        
        # Save file temporarily
        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content_bytes = await file.read()
            tmp.write(content_bytes)
            tmp_path = tmp.name
        
        try:
            # 1) Save file information to database
            new_doc = save_document(
                db=db,
                filename=file.filename,
                user_id=db_user.id,
                domain_id=db_user.domain_id,
            )
            print(f"[upload] File info saved, ID: {new_doc.id}")

            # 2) Process document using async MCP client
            try:
                mcp_response = await docling_client.load_and_split_async(
                    file_path=tmp_path,
                    chunk_size=500,
                    chunk_overlap=50
                )
            except Exception as docling_error:
                print(f"[upload] Docling processing error: {docling_error}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to process document {file.filename}: {str(docling_error)}"
                )
            
            # Convert dicts back to Document objects
            docs_chunks = [
                Document(
                    page_content=chunk["page_content"], 
                    metadata=chunk["metadata"]
                ) 
                for chunk in mcp_response
                if isinstance(chunk, dict) and "page_content" in chunk
            ]
            
            if not docs_chunks:
                print(f"[upload] Warning: No chunks created from {file.filename}")
                continue

            # 3) Add metadata to chunks
            for doc_chunk in docs_chunks:
                if not isinstance(doc_chunk.metadata, dict):
                    doc_chunk.metadata = {}
                doc_chunk.metadata.update({
                    "domain_id": new_doc.domain_id,
                    "doc_id": new_doc.id,
                    "user_id": new_doc.user_id,
                    "source": file.filename,
                    "file_size_mb": round(len(content_bytes) / 1024 / 1024, 2),
                    "processing_timestamp": asyncio.get_event_loop().time()
                })

            print(f"[upload] Processing {len(docs_chunks)} chunks for file: {file.filename}")

            # 4) Save chunks to database in small batches
            try:
                for i in range(0, len(docs_chunks), BATCH_SIZE):
                    batch = docs_chunks[i:i + BATCH_SIZE]
                    save_chunks(
                        db,
                        chunks_list=batch,
                        doc_id=new_doc.id,
                        user_id=new_doc.user_id,
                        domain_id=new_doc.domain_id,
                        batch_size=len(batch),
                    )
                    print(f"[upload] Batch {i//BATCH_SIZE + 1} saved to database")
                    await asyncio.sleep(0.1)
                
                db.commit()
                print(f"[upload] All chunks saved to database")
                
                # Track this doc for graph update
                processed_doc_ids.append(new_doc.id)
                
            except Exception as save_error:
                print(f"[upload] Database save error: {save_error}")
                db.rollback()
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to save chunks to database: {str(save_error)}"
                )

            # 5) Add to Vector DB in small batches
            try:
                vector_batch_size = 25
                for i in range(0, len(docs_chunks), vector_batch_size):
                    batch = docs_chunks[i:i + vector_batch_size]
                    
                    # Run in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, add_documents, batch)
                    
                    print(f"[upload] Batch {i//vector_batch_size + 1} added to vector DB")
                    await asyncio.sleep(0.2)
                
                # Persist changes
                await loop.run_in_executor(None, persist)
                print(f"[upload] All chunks saved to Vector DB")
                
            except Exception as vector_error:
                print(f"[upload] Vector DB error: {vector_error}")
                traceback.print_exc()
                # Don't fail the entire upload if vector DB fails
                print(f"[upload] Continuing despite vector DB error")

            total_chunks += len(docs_chunks)
            file_counts.append({
                "filename": file.filename, 
                "chunks": len(docs_chunks),
                "size_mb": round(len(content_bytes) / 1024 / 1024, 2),
                "status": "success"
            })
            
            print(f"[upload] Finished processing {file.filename}: {len(docs_chunks)} chunks")

        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            print(f"[upload] General error processing {file.filename}: {e}")
            traceback.print_exc()
            
            # Add failed file to results
            file_counts.append({
                "filename": file.filename,
                "chunks": 0,
                "size_mb": round(len(content_bytes) / 1024 / 1024, 2),
                "status": "failed",
                "error": str(e)
            })
            
        finally:
            # Clean up temp file
            try:
                os.remove(tmp_path)
            except FileNotFoundError:
                pass
            gc.collect()

    # 6) Update Graph Database (after all files are processed)
    graph_update_results = []
    if graph_available and graph_client and processed_doc_ids:
        print(f"[upload] Updating graph database for {len(processed_doc_ids)} documents...")
        
        for doc_id in processed_doc_ids:
            try:
                graph_result = await graph_client.update_graph(
                    domain_id=db_user.domain_id,
                    doc_id=doc_id,
                    user_id=db_user.id
                )
                
                if graph_result.get("status") == "success":
                    print(f"[upload] Graph updated for doc_id={doc_id}: "
                          f"{graph_result.get('nodes_added', 0)} nodes, "
                          f"{graph_result.get('triplets_extracted', 0)} triplets")
                    graph_update_results.append({
                        "doc_id": doc_id,
                        "status": "success",
                        "nodes_added": graph_result.get('nodes_added', 0),
                        "triplets_extracted": graph_result.get('triplets_extracted', 0)
                    })
                else:
                    print(f"[upload] Graph update failed for doc_id={doc_id}: {graph_result.get('message')}")
                    graph_update_results.append({
                        "doc_id": doc_id,
                        "status": "failed",
                        "error": graph_result.get('message', 'Unknown error')
                    })
                    
            except Exception as graph_error:
                print(f"[upload] Graph update error for doc_id={doc_id}: {graph_error}")
                graph_update_results.append({
                    "doc_id": doc_id,
                    "status": "error",
                    "error": str(graph_error)
                })
        
        # Close graph client
        try:
            if hasattr(graph_client, 'session') and graph_client.session:
                await graph_client.session.close()
        except:
            pass

    print(f"[upload] Finished uploading all files: {total_chunks} total chunks")

    # Count successful vs failed files
    successful_files = [f for f in file_counts if f.get("status") == "success"]
    failed_files = [f for f in file_counts if f.get("status") == "failed"]

    response = {
        "message": f"Processed {len(files)} files: {len(successful_files)} successful, {len(failed_files)} failed",
        "total_chunks": total_chunks,
        "files": file_counts,
        "system_memory_usage": f"{psutil.virtual_memory().percent:.1f}%",
        "summary": {
            "total_files": len(files),
            "successful": len(successful_files),
            "failed": len(failed_files)
        }
    }
    
    # Add graph update information if available
    if graph_update_results:
        successful_graph_updates = [g for g in graph_update_results if g.get("status") == "success"]
        response["graph_updates"] = {
            "enabled": True,
            "total_documents": len(processed_doc_ids),
            "successful": len(successful_graph_updates),
            "failed": len(graph_update_results) - len(successful_graph_updates),
            "details": graph_update_results,
            "total_nodes_added": sum(g.get("nodes_added", 0) for g in successful_graph_updates),
            "total_triplets_extracted": sum(g.get("triplets_extracted", 0) for g in successful_graph_updates)
        }
    elif ENABLE_GRAPH_AUTO_UPDATE and not graph_available:
        response["graph_updates"] = {
            "enabled": True,
            "status": "unavailable",
            "message": "Graph MCP service not available"
        }
    else:
        response["graph_updates"] = {
            "enabled": False,
            "message": "Graph auto-update is disabled"
        }
    
    # If some files failed, return 207 (Multi-Status) instead of 200
    if failed_files and successful_files:
        raise HTTPException(status_code=207, detail=response)
    elif failed_files:
        raise HTTPException(status_code=500, detail=response)
    
    return response

# Optional: Add endpoint to check docling service health
@router.get("/docling-health", dependencies=[Depends(require_admin)])
async def check_docling_health():
    """Check if the docling MCP server is running"""
    docling_client = DoclingHttpClient(base_url="http://127.0.0.1:5000")
    is_healthy = await docling_client.health_check_async()
    
    return {
        "docling_service": "healthy" if is_healthy else "unhealthy",
        "base_url": docling_client.base_url,
        "status": "ok" if is_healthy else "error"
    }

# Add endpoint to check graph service health
@router.get("/graph-health", dependencies=[Depends(require_admin)])
async def check_graph_health():
    """Check if the graph MCP server is running"""
    try:
        async with GraphMCPClient(mcp_url=GRAPH_MCP_URL) as client:
            health = await client.health_check()
            return {
                "graph_service": "healthy" if health.get("status") == "healthy" else "unhealthy",
                "base_url": GRAPH_MCP_URL,
                "status": "ok" if health.get("status") == "healthy" else "error",
                "details": health
            }
    except Exception as e:
        return {
            "graph_service": "unhealthy",
            "base_url": GRAPH_MCP_URL,
            "status": "error",
            "error": str(e)
        }

# Add endpoint to manually trigger graph update for a document
@router.post("/update-graph/{doc_id}", dependencies=[Depends(require_admin)])
async def manually_update_graph(
    doc_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal)
):
    """Manually trigger graph update for a specific document"""
    
    # Verify user
    db_user = db.query(User).filter(User.username == principal.sub).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="User not found")
    
    try:
        async with GraphMCPClient(mcp_url=GRAPH_MCP_URL) as client:
            result = await client.update_graph(
                domain_id=db_user.domain_id,
                doc_id=doc_id,
                user_id=db_user.id
            )
            
            return {
                "status": "success",
                "doc_id": doc_id,
                "graph_update": result
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update graph: {str(e)}"
        )