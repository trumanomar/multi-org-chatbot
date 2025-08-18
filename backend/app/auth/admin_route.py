<<<<<<< HEAD
=======
# app/auth/admin_route.py
>>>>>>> 05c442592b57776dae5c4587a0e474f22d3cb1c8
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.DB.db import get_db
<<<<<<< HEAD
from app.auth.schemas import CreateUserRequest, DeleteDocumentRequest, DeleteDocumentResponse
from app.Models.tables import User, RoleEnum, Docs, Chunk
from app.VectorDB.DB import delete_chunks_vectors  # Added import

=======
from app.auth.schemas import CreateUserRequest
from app.Models.tables import User, RoleEnum, Docs, Chunk
>>>>>>> 05c442592b57776dae5c4587a0e474f22d3cb1c8
from app.auth.utils import hash_password
from app.auth.dependencies import (
    require_admin,
    get_current_user_db,
    get_current_principal,
    enforce_same_domain_query,
    Principal,
)
from app.VectorDB.DB import delete_vectors_for_doc

router = APIRouter(prefix="/admin", tags=["Admin"])

# -------------------------------------------------------------------------
# USERS
# -------------------------------------------------------------------------

@router.post("/create_user", dependencies=[Depends(require_admin)])
def create_user(
    request: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_db),
):
<<<<<<< HEAD
     # Only org admins can create users (super-admin does NOT create users)
    if current_user.role_based != RoleEnum.admin.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only org admins can create users"
        )
    # no role check needed; require_admin already enforced
    existing = db.query(User).filter(User.username == request.username).first()
    if existing:
=======
    if current_user.role_based != RoleEnum.admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only org admins can create users")

    if db.query(User).filter(User.username == request.username).first():
>>>>>>> 05c442592b57776dae5c4587a0e474f22d3cb1c8
        raise HTTPException(status_code=400, detail="Username already registered")

    user = User(
        username=request.username,
        email=request.email,
        password=hash_password(request.password),
        role_based=RoleEnum.user.value,
        domain_id=current_user.domain_id,
    )
    db.add(user)
    db.commit()
<<<<<<< HEAD
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

=======
    db.refresh(user)
    return {"message": "User created successfully", "user_id": user.id}

@router.get("/users", dependencies=[Depends(require_admin)])
def list_users(
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    # Return users in THIS admin's domain (role=user)
    q = enforce_same_domain_query(db.query(User), User, principal).filter(
        User.role_based == RoleEnum.user.value
    )
    users = q.order_by(User.id).all()
    # Stable envelope for frontend
    return {
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "domain_id": u.domain_id,
                "role": u.role_based,
                "created_at": u.created_at,
            }
            for u in users
        ]
    }

# -------------------------------------------------------------------------
# DOCS + CHUNKS
# -------------------------------------------------------------------------

@router.get("/docs", dependencies=[Depends(require_admin)])
def list_docs(
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    docs = enforce_same_domain_query(db.query(Docs), Docs, principal).order_by(Docs.id).all()
    out = []
    for doc in docs:
        chunk_count = db.query(Chunk).filter(Chunk.doc_id == doc.id).count()
        out.append(
            {
                "id": doc.id,
                "name": doc.name,
                "user_id": doc.user_id,
                "domain_id": doc.domain_id,
                "chunk_count": chunk_count,
                "created_at": doc.created_at,
            }
        )
    return {"docs": out}  # ← stable envelope

@router.get("/chunks", dependencies=[Depends(require_admin)])
def list_chunks(
    doc_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    # Ensure the doc belongs to this admin’s domain
    doc = enforce_same_domain_query(
        db.query(Docs).filter(Docs.id == doc_id), Docs, principal
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = db.query(Chunk).filter(Chunk.doc_id == doc_id).order_by(Chunk.id).all()
    return {
        "doc_id": doc_id,
        "chunks": [
            {
                "id": c.id,
                "content": c.content,
                "meta_data": c.meta_data,
                "created_at": c.created_at,
            }
            for c in chunks
        ],
    }

@router.delete("/docs/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_doc(
    doc_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    # 1) Domain guard
    doc = enforce_same_domain_query(
        db.query(Docs).filter(Docs.id == doc_id), Docs, principal
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or not in your domain")

    # 2) Delete vectors first
    try:
        delete_vectors_for_doc(doc_id=doc.id, domain_id=principal.domain_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector delete failed: {e}")

    # 3) Delete SQL rows
    try:
        db.query(Chunk).filter(Chunk.doc_id == doc.id).delete(synchronize_session=False)
        db.delete(doc)
        db.commit()
        # 204 No Content on success
        return
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"SQL delete failed: {e}")
>>>>>>> 05c442592b57776dae5c4587a0e474f22d3cb1c8
