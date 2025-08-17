from fastapi import Depends, APIRouter, HTTPException, status
from sqlalchemy.orm import Session
from app.DB.db import get_db
from app.auth.dependencies import get_current_principal, require_super_admin, Principal
from app.Models.tables import Domain, User, RoleEnum
from app.auth.utils import hash_password
from app.auth.schemas import CreateAdminRequest

from fastapi import APIRouter
router = APIRouter(prefix="/super-admin", tags=["Super Admin"])

@router.get("/dashboard")
def dashboard(_=Depends(require_super_admin)):
    return {"message": "Welcome Super Admin"}

@router.post("/admin/create")
def create_admin(
    request: CreateAdminRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal)
):
    if principal.role != RoleEnum.super_admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only super admins can create admins")

    # TODO: pass a domain_id in request or decide a default; using 1 for now.
    domain_id = 1

    exists = db.query(User).filter(User.email == request.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_admin = User(
        username=request.username,
        email=request.email,
        password=hash_password(request.password),
        role_based=RoleEnum.admin.value,
        domain_id=domain_id,
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return {"message": "Admin created successfully", "admin_id": new_admin.id}
