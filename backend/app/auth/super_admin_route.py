# app/auth/super_admin_route.py
from fastapi import Depends, APIRouter, HTTPException, status
from sqlalchemy.orm import Session
from starlette.status import HTTP_425_TOO_EARLY
from app.DB.db import get_db
from app.auth.dependencies import get_current_principal, require_super_admin, Principal,get_current_user_db
from app.Models.tables import Domain, User, RoleEnum
from app.auth.utils import hash_password
from app.auth.schemas import CreateSuperAdminRequest

from pydantic import BaseModel, EmailStr

from app.DB.db import get_db
from app.auth.dependencies import require_super_admin, get_current_principal, Principal
from app.Models.tables import Domain, User, RoleEnum, Docs, Chunk
from app.auth.utils import hash_password
from app.auth.schemas import CreateAdminRequest as _CreateAdminReq, CreateDomainRequest as _CreateDomainReq  # optional if you already had them

router = APIRouter(prefix="/super-admin", tags=["Super Admin"])

# ---------- Schemas (light) ----------
class DomainCreate(BaseModel):
    name: str

class CreateAdminRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    domain_id: int

@router.get("/dashboard")
def dashboard(_=Depends(require_super_admin)):
    return {"message": "Welcome Super Admin"}
@router.post("/super-admin/create")
def create_super_admin(
    request: CreateSuperAdminRequest,
    db: Session = Depends(get_db)
):
    # check email exists
    exists = db.query(User).filter(User.email == request.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    # create domain
    new_domain = Domain(name=request.domain_name)
    db.add(new_domain)
    db.commit()
    db.refresh(new_domain)

    # create super admin
    super_admin = User(
        username=request.username,
        email=request.email,
        password=hash_password(request.password),
        role_based=RoleEnum.admin.value,
        domain_id=new_domain.id
    )
    db.add(super_admin)
    db.commit()
    db.refresh(super_admin)

    return {
        "message": "Super admin and domain created successfully",
        "super_admin_id": super_admin.id,
        "domain_id": new_domain.id
    }
