from fastapi import APIRouter, UploadFile, File
import os
from app.VectorDB.DB import vectorstore,embedding_function
from app.utilis.utils import load_and_split
from tempfile import NamedTemporaryFile
from app.VectorDB.DB import add_documents, persist

router = APIRouter(prefix="/admin", tags=["Admin"])
BATCH_SIZE = 20  # no of documents to store in each batch
@router.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    total_chunks = 0
    for file in files:
        suffix = os.path.splitext(file.filename)[-1]
        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        docs = load_and_split(tmp_path)
        
#Add metadata to each document
        for doc in docs:
            doc.metadata["source_file"] = file.filename

#Add documents to the vector store in batches
        for i in range(0, len(docs), BATCH_SIZE):
            batch = docs[i:i+BATCH_SIZE]
            vectorstore.add_documents(batch)

# Safely persist if the method exists
        if hasattr(vectorstore, "persist"):
            vectorstore.persist()

        total_chunks += len(docs)
        os.remove(tmp_path)

    return {"message": f"Indexed {total_chunks} chunks from {len(files)} file(s)"}


#Health check endpoint
