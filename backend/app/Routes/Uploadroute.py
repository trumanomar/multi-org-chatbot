# app/Routes/Uploadroute.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import os, traceback
from tempfile import NamedTemporaryFile
from sqlalchemy.orm import Session
import json
from app.utilis.utils import load_and_split_func
from app.VectorDB.DB import add_documents, persist
from app.DB.db import get_db
from app.Models.tables import User
from app.DB.save_docs import save_document
from app.DB.save_chunks import save_chunks
from app.auth.dependencies import require_admin, get_current_principal, Principal

router = APIRouter(prefix="/admin", tags=["Admin"])
BATCH_SIZE = 500  # safer for large files

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
        # should never happen if require_admin is enforced and token is correct
        raise HTTPException(status_code=403, detail="Missing domain in token")

    # resolve admin DB user from JWT subject
    db_user = db.query(User).filter(User.username == principal.sub).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="DB user not found")

    total_chunks = 0
    file_counts = []

    for file in files:
        suffix = os.path.splitext(file.filename)[-1].lower()
        if suffix not in ALLOWED_EXTS:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type: {suffix}. Allowed: {sorted(ALLOWED_EXTS)}",
            )

        print(f"[upload] start: {file.filename}")
        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content_bytes = await file.read()
            tmp.write(content_bytes)
            tmp_path = tmp.name
        print(f"[upload] temp saved: {tmp_path}")

        try:
            # 1) save doc row (admin's domain)
            new_doc = save_document(
                db=db,
                filename=file.filename,
                user_id=db_user.id,
                domain_id=db_user.domain_id,
            )
            print(f"[upload] doc row id={new_doc.id}")

            # 2) chunk the file - now returns Document objects
            docs_chunks = load_and_split_func(tmp_path) or []
            print(f"[upload] chunked: {len(docs_chunks)} chunks")
            
            # DEBUG: Check what we got from load_and_split_func
            if docs_chunks:
                print(f"[upload] DEBUG: First chunk type: {type(docs_chunks[0])}")
                print(f"[upload] DEBUG: First chunk content preview: {docs_chunks[0].page_content[:100] if hasattr(docs_chunks[0], 'page_content') else 'NO PAGE_CONTENT'}")
                print(f"[upload] DEBUG: First chunk metadata: {docs_chunks[0].metadata if hasattr(docs_chunks[0], 'metadata') else 'NO METADATA'}")

            # 3) Update metadata for each Document object
            for doc_chunk in docs_chunks:
                doc_chunk.metadata["domain_id"] = new_doc.domain_id
                doc_chunk.metadata["doc_id"] = new_doc.id
                doc_chunk.metadata["user_id"] = new_doc.user_id
                page = doc_chunk.metadata.get("page")
                doc_chunk.metadata["source"] = (
                    f"{file.filename}#page={int(page)+1}" if isinstance(page, int) else file.filename
                )

            # 4) Convert Document objects to dictionaries for save_chunks
            chunks_dicts = []
            for doc_chunk in docs_chunks:
                md = dict(doc_chunk.metadata) if doc_chunk.metadata else {}
                chunk_dict = {
                    "content": doc_chunk.page_content or "",
                    "metadata": json.dumps(md, ensure_ascii=False)  
                }
                chunks_dicts.append(chunk_dict)
            
            print(f"[upload] DEBUG: About to call save_chunks with {len(chunks_dicts)} chunks")
            print(f"[upload] DEBUG: First chunk dict: {chunks_dicts[0] if chunks_dicts else 'NO CHUNKS'}")

            # Call save_chunks and catch any errors
            try:
                save_chunks(
                db,
                chunks_list=docs_chunks,
                doc_id=new_doc.id,
                user_id=new_doc.user_id,
                domain_id=new_doc.domain_id,
                batch_size=BATCH_SIZE,
            )
                db.commit()
                print(f"[upload] chunks saved to SQL successfully")
            except Exception as save_error:
                print(f"[upload] ERROR in save_chunks: {save_error}")
                traceback.print_exc()
                raise

            # 5) add to vector DB (now with proper Document objects)
            if docs_chunks:
                try:
                    add_documents(docs_chunks)
                    persist()
                    print(f"[upload] chunks persisted to Chroma")
                except Exception as vector_error:
                    print(f"[upload] ERROR in vector store: {vector_error}")
                    traceback.print_exc()
                    raise

            total_chunks += len(docs_chunks)
            file_counts.append({"filename": file.filename, "chunks": len(docs_chunks)})

        except Exception as e:
            print(f"[upload] GENERAL ERROR: {e}")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Upload failed for {file.filename}: {e}")
        finally:
            try:
                os.remove(tmp_path)
            except FileNotFoundError:
                pass

    return {
        "message": f"Saved {len(files)} document(s) and {total_chunks} chunk(s)",
        "files": file_counts,
    }