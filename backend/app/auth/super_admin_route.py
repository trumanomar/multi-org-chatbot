# app/auth/super_admin_route.py
from fastapi import Depends, APIRouter, HTTPException, status
from sqlalchemy.orm import Session

from pydantic import BaseModel, EmailStr

from app.DB.db import get_db
from app.auth.dependencies import require_super_admin, get_current_principal, Principal
from app.Models.tables import Domain, User, RoleEnum, Docs, Chunk
from app.auth.utils import hash_password
from app.auth.schemas import CreateAdminRequest as _CreateAdminReq, CreateDomainRequest as _CreateDomainReq  # optional if you already had them
from app.auth.password_validation import validate_password, get_password_requirements

router = APIRouter(prefix="/super-admin", tags=["Super Admin"])

# ---------- Schemas (light) ----------
class DomainCreate(BaseModel):
    name: str
    active: bool = True

class CreateAdminRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    domain_id: int

@router.get("/dashboard")
def dashboard(_=Depends(require_super_admin)):
    return {"message": "Welcome Super Admin"}
@router.get("/password-requirements")
def get_password_requirements_endpoint():
    """Get password requirements for frontend display"""
    return get_password_requirements()
# ---------- Domains ----------
@router.post("/domain/create")
def create_domain(
    data: DomainCreate,
    db: Session = Depends(get_db),
    _sa: Principal = Depends(require_super_admin),
):
    if db.query(Domain).filter(Domain.name == data.name,Domain.active==data.active).first():
        raise HTTPException(status_code=400, detail="Domain already exists")
    d = Domain(name=data.name,active=data.active)
    db.add(d)
    db.commit()
    db.refresh(d)
    return {"message": "Domain created", "domain_id": d.id}

@router.get("/domains")
def list_domains(
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    if principal.role != RoleEnum.super_admin.value:
        raise HTTPException(status_code=403, detail="Super admin only")
    domains = db.query(Domain).order_by(Domain.id).all()
    return {
        "domains": [
            {"id": d.id, "name": d.name, "created_at": d.created_at} for d in domains
        ]
    }
# delete domain    
@router.delete("/domain/{domain_id}")
def delete_domain(
    domain_id: int,
    db: Session = Depends(get_db),
    _sa: Principal = Depends(require_super_admin),
):
    domain = db.query(Domain).get(domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    db.delete(domain)
    db.commit()
    return {"message": "Domain deleted"}
# ---------- Admins ----------
@router.post("/admin/create")
def create_admin(
    request: CreateAdminRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    if principal.role != RoleEnum.super_admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only super admins can create admins")

    # Validate password strength
    try:
        validate_password(request.password)
    except HTTPException as e:
        # Re-raise with more context
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Password validation failed: {e.detail}"
        )

    domain = db.query(Domain).get(request.domain_id)
    if not domain:
        raise HTTPException(status_code=400, detail="Invalid domain_id")

    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check if username already exists
    if db.query(User).filter(User.username == request.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")

    admin = User(
        username=request.username,
        email=request.email,
        password=hash_password(request.password),
        role_based=RoleEnum.admin.value,
        domain_id=request.domain_id,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return {"message": "Admin created successfully", "admin_id": admin.id}
@router.get("/admins")
def list_admins(
    db: Session = Depends(get_db),
    _sa: Principal = Depends(require_super_admin),
):
    admins = db.query(User).filter(User.role_based == RoleEnum.admin.value).order_by(User.id).all()
    return {
        "admins": [
            {
                "id": a.id,
                "username": a.username,
                "email": a.email,
                "domain_id": a.domain_id,
                "created_at": a.created_at,
            }
            for a in admins
        ]
    }

# ---------- Docs (global) ----------
@router.get("/docs")
def list_docs_global(
    db: Session = Depends(get_db),
    _sa: Principal = Depends(require_super_admin),
):
    docs = db.query(Docs).order_by(Docs.id).all()
    out = []
    for doc in docs:
        chunk_count = db.query(Chunk).filter(Chunk.doc_id == doc.id).count()
        out.append(
            {
                "id": doc.id,
                "name": doc.name,
                "domain_id": doc.domain_id,
                "user_id": doc.user_id,
                "chunk_count": chunk_count,
                "created_at": doc.created_at,
            }
        )
    return {"docs": out}

# ---------- KPI snapshot ----------
@router.get("/stats")
def super_admin_stats(
    db: Session = Depends(get_db),
    _sa: Principal = Depends(require_super_admin),
):
    domains = db.query(Domain).count()
    admins  = db.query(User).filter(User.role_based == RoleEnum.admin.value).count()
    docs    = db.query(Docs).count()
    return {"domains": domains, "admins": admins, "docs": docs, "system_health": "ok"}
