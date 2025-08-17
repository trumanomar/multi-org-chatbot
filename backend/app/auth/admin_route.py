from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.DB.db import get_db
from app.auth.schemas import CreateUserRequest, DeleteDocumentRequest, DeleteDocumentResponse
from app.Models.tables import User, RoleEnum, Docs, Chunk
from app.VectorDB.DB import delete_chunks_vectors  # Added import

from app.auth.utils import hash_password
from app.auth.dependencies import get_current_principal, require_admin_or_super, Principal
from app.auth.dependencies import require_admin, get_current_user_db

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/create_user")
def create_user(
    request: CreateUserRequest,
    db: Session = Depends(get_db),
    principal = Depends(require_admin),               # ensures role == admin
    current_user: User = Depends(get_current_user_db) # now guaranteed to exist
):
     # Only org admins can create users (super-admin does NOT create users)
    if current_user.role_based != RoleEnum.admin.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only org admins can create users"
        )
    # no role check needed; require_admin already enforced
    existing = db.query(User).filter(User.username == request.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")

    new_user = User(
        username=request.username,
        email=request.email,
        password=hash_password(request.password),
        role_based=RoleEnum.user.value,
        domain_id=current_user.domain_id,  # inherit admin's domain
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully", "user_id": new_user.id}
@router.get("/docs")
def list_docs(db: Session = Depends(get_db)):
    docs = (
        db.query(Docs)
        .all()
    )
    results = []
    for doc in docs:
        chunk_count = db.query(Chunk).filter(Chunk.doc_id == doc.id).count()
        results.append({
            "id": doc.id,
            "filename": doc.name,
            "user_id": doc.user_id,
            "domain_id": doc.domain_id,
            "chunk_count": chunk_count,
            "created_at": doc.created_at,
        })
    return results


# ✅ Get list of chunks by doc_id
@router.get("/chunks")
def list_chunks(doc_id: int = Query(...), db: Session = Depends(get_db)):
    chunks = db.query(Chunk).filter(Chunk.doc_id == doc_id).all()
    return [
        {
            "id": c.id,
            "content": c.content,
            "vector_id": c.doc_id,
            "created_at": c.created_at,
        }
        for c in chunks
    ]


# ✅ Delete document + chunks + vectors
@router.delete("/docs/{doc_id}", response_model=DeleteDocumentResponse)
def delete_doc(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Docs).filter(Docs.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = db.query(Chunk).filter(Chunk.doc_id == doc_id).all()
    
    vectors_deleted = 0
    vector_ids = [c.doc_id for c in chunks if c.doc_id]
    if vector_ids:
        vectors_deleted = delete_chunks_vectors(vector_ids)

    chunks_count = len(chunks)
    for c in chunks:
        db.delete(c)
    db.delete(doc)
    db.commit()

    return DeleteDocumentResponse(
        message=f"Document {doc_id} deleted successfully",
        doc_id=doc_id,
        chunks_deleted=chunks_count,
        vectors_deleted=vectors_deleted
    )

