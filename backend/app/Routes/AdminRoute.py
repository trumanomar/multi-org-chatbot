from fastapi import APIRouter, UploadFile, File
import os
from app.VectorDB.DB import vectorstore
from app.utilis.utils import load_and_split
from tempfile import NamedTemporaryFile

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    all_docs = []
    for file in files:
        suffix = os.path.splitext(file.filename)[-1]
        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        docs = load_and_split(tmp_path)
        for doc in docs:
         doc.metadata["source_file"] = file.filename
   
        all_docs.extend(docs)
        os.remove(tmp_path)
    vectorstore.add_documents(all_docs)
    vectorstore.persist()
    return {"message": f"Indexed {len(all_docs)} chunks from {len(files)} file(s)"}
