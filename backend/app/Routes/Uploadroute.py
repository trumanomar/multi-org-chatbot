# app/Routes/Uploadroute.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import os, traceback
from tempfile import NamedTemporaryFile
from sqlalchemy.orm import Session

from app.utilis.utils import load_and_split
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
            # 1) save doc row (admin’s domain)
            new_doc = save_document(
                db=db,
                filename=file.filename,
                user_id=db_user.id,
                domain_id=db_user.domain_id,
            )
            print(f"[upload] doc row id={new_doc.id}")

            # 2) chunk the file
            docs_chunks = load_and_split(tmp_path) or []
            print(f"[upload] chunked: {len(docs_chunks)} chunks")

            # 3) enrich metadata, then save chunks in SQL
            for d in docs_chunks:
                md = d.metadata or {}
                md["domain_id"] = new_doc.domain_id
                md["doc_id"] = new_doc.id
                md["user_id"] = new_doc.user_id
                page = md.get("page")
                md["source"] = (
                    f"{file.filename}#page={int(page)+1}" if isinstance(page, int) else file.filename
                )
                d.metadata = md

            save_chunks(
                db=db,
                chunks_list=docs_chunks,
                doc_id=new_doc.id,
                user_id=new_doc.user_id,
                domain_id=new_doc.domain_id,
                batch_size=BATCH_SIZE,
            )
            print(f"[upload] chunks saved to SQL")

            # 4) add to vector DB (metadata already set)
            if docs_chunks:
                add_documents(docs_chunks)
                persist()
                print(f"[upload] chunks persisted to Chroma")

            total_chunks += len(docs_chunks)
            file_counts.append({"filename": file.filename, "chunks": len(docs_chunks),"domain_id":domain_id,"doc_id":new_doc.id,"admin_id":user_id})

        except Exception as e:
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