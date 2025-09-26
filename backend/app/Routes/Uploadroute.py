# app/Routes/Uploadroute.py - Updated version
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
from langchain.docstore.document import Document

router = APIRouter(prefix="/admin", tags=["Admin"])
BATCH_SIZE = 100
ALLOWED_EXTS = {".pdf", ".docx", ".txt", ".csv", ".xlsx", ".md"}

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

    # Initialize docling client
    docling_client = DoclingHttpClient(base_url="http://127.0.0.1:5000")
    
    # Check if docling service is healthy
    if not await docling_client.health_check_async():
        raise HTTPException(
            status_code=503, 
            detail="Docling service is not available. Please ensure the MCP server is running."
        )
        
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
                    chunk_size=500,  # You can make these configurable
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