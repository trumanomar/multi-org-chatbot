from fastapi import APIRouter
from app.VectorDB.DB import vectorstore  

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/docs")
def get_docs():
    results = vectorstore.similarity_search("", k=1000)  

    docs_list = [
        {
            "content": doc.page_content,
            "metadata": doc.metadata
        }
        for doc in results
    ]

    return {"docs": docs_list}
