# app/auth/admin_route.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.DB.db import get_db
from app.auth.schemas import CreateUserRequest
from app.Models.tables import User, RoleEnum, Docs, Chunk
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
    if current_user.role_based != RoleEnum.admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only org admins can create users")

    if db.query(User).filter(User.username == request.username).first():
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
#delete users
@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    user = enforce_same_domain_query(db.query(User), User, principal).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}
#update role
@router.put("/users/role/{user_id}",status_code=status.HTTP_204_NO_CONTENT,dependencies=[Depends(require_admin)])
def update_role(
    user_id: int,
    new_role: RoleEnum,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    user = enforce_same_domain_query(db.query(User), User, principal).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if new_role not in [RoleEnum.user, RoleEnum.admin]:
        raise HTTPException(status_code=400, detail="Invalid role")
    user.role_based = new_role.value
    db.commit()
    return {"message": "User role updated successfully"}
#update email
@router.put("/users/{user_id}/email",status_code=status.HTTP_204_NO_CONTENT,dependencies=[Depends(require_admin)])
def update_email(
    user_id: int,
    new_email: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    user = enforce_same_domain_query(db.query(User), User, principal).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if db.query(User).filter(User.email == new_email).first():
        raise HTTPException(status_code=400, detail="Email already in use")
    user.email = new_email
    db.commit()
    return {"message": "User email updated successfully"}
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
