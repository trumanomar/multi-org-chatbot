from fastapi import APIRouter, UploadFile, File, HTTPException
import os
from tempfile import NamedTemporaryFile

from app.utilis.utils import load_and_split
from app.VectorDB.DB import add_documents, persist  # use the helpers; no need for vectorstore here

router = APIRouter(prefix="/admin", tags=["Admin"])
BATCH_SIZE = 64  # not used in this simple helper path; see batching version below

@router.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    total_chunks = 0
    file_counts = []

    for file in files:
        suffix = os.path.splitext(file.filename)[-1]
        # Save to a temp file
        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Split into LangChain Documents
            docs = load_and_split(tmp_path) or []

            # Overwrite metadata["source"] to the user-facing filename (+page)
            for d in docs:
                page = d.metadata.get("page")
                d.metadata["source"] = f"{file.filename}#page={page + 1}" if page is not None else file.filename

            # Add to vector store and persist
            if docs:
                add_documents(docs)
                persist()

            total_chunks += len(docs)
            file_counts.append({"filename": file.filename, "chunks": len(docs)})

        finally:
            # Always remove the temp file
            try:
                os.remove(tmp_path)
            except FileNotFoundError:
                pass

    return {
        "message": f"Indexed {total_chunks} chunks from {len(files)} file(s)",
        "files": file_counts,
    }
