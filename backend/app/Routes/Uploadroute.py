from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import os
from tempfile import NamedTemporaryFile
from sqlalchemy.orm import Session

from app.utilis.utils import load_and_split
from app.VectorDB.DB import add_documents, persist
from app.DB.db import get_db
from app.Models.tables import Docs, Chunk, User
from app.DB.save_docs import save_document
from app.DB.save_chunks import save_chunks

# NEW: auth deps
from app.auth.dependencies import require_admin, get_current_principal, Principal

router = APIRouter(prefix="/admin", tags=["Admin"])
BATCH_SIZE = 64

@router.post("/upload", dependencies=[Depends(require_admin)])
async def upload_files(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    # resolve DB user from token
    user = db.query(User).filter(User.username == principal.sub).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    user_id = user.id
    domain_id = user.domain_id

    total_chunks = 0
    file_counts = []

    for file in files:
        suffix = os.path.splitext(file.filename)[-1]

        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content_bytes = await file.read()
            tmp.write(content_bytes)
            tmp_path = tmp.name

        try:
            # 1) save doc row
            new_doc = save_document(
                filename=file.filename,
                user_id=user_id,
                domain_id=domain_id,
            )

            # 2) chunk
            docs_chunks = load_and_split(tmp_path) or []

            # enrich metadata for DB + vector filter
            for d in docs_chunks:
                d.metadata.update({
                    "source": file.filename,
                    "user_id": user_id,
                    "domain_id": domain_id,
                    "doc_id": new_doc.id,
                })

            # 3) save chunks in relational DB
            save_chunks(
                chunks_list=docs_chunks,
                doc_id=new_doc.id,
                user_id=user_id,
                domain_id=domain_id,
            )

            # 4) add to vector DB (with metadata attached)
            if docs_chunks:
                add_documents(docs_chunks)
                persist()

            total_chunks += len(docs_chunks)
            file_counts.append({"filename": file.filename, "chunks": len(docs_chunks)})

        finally:
            try:
                os.remove(tmp_path)
            except FileNotFoundError:
                pass

    return {
        "message": f"Saved {len(files)} document(s) and {total_chunks} chunk(s)",
        "files": file_counts,
    }
