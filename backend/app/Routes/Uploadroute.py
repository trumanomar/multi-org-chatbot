from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import os
from tempfile import NamedTemporaryFile
from sqlalchemy.orm import Session

from app.utilis.utils import load_and_split
from app.VectorDB.DB import add_documents, persist
from app.DB.db import get_db
from app.Models.tables import Docs, Chunk
from app.DB.save_docs import save_document
from app.DB.save_chunks import save_chunks
router = APIRouter(prefix="/admin", tags=["Admin"])
BATCH_SIZE = 64

@router.post("/upload")
async def upload_files(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    total_chunks = 0
    file_counts = []

    for file in files:
        suffix = os.path.splitext(file.filename)[-1]

        # Save file temporarily
        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content_bytes = await file.read()
            tmp.write(content_bytes)
            tmp_path = tmp.name

        try:
            # 1️⃣ Save full document in DB
            new_doc = save_document(
                filename=file.filename,
                user_id=1,  # Replace with actual user ID
                domain_id=1,  # Replace with actual domain ID
            )
            docs_chunks = load_and_split(tmp_path) or []

            chunks = save_chunks(
                chunks_list=docs_chunks,
                doc_id=new_doc.id,
                user_id=new_doc.user_id,
                domain_id=new_doc.domain_id
            )

            # 3️⃣ إضافة الـ chunks لـ Vector DB
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
