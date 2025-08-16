from fastapi import Depends, APIRouter, HTTPException 
from sqlalchemy.orm import Session 
from app.DB.db import get_db 
from app.auth.dependencies import require_super_admin, get_current_user_db

from app.Models.tables import Domain, User, RoleEnum 
from app.auth.utils import hash_password 
from app.auth.schemas import RegisterAdmin, DomainOut, UserOut
from app.auth.schemas import CreateAdminRequest, CreateUserRequest
from app.auth.dependencies import get_current_principal, Principal





router = APIRouter(prefix="/admin", tags=["Admin"])
@router.get("/dashboard")
def dashboard(_=Depends(require_super_admin)):
    return {"message": "Welcome Super Admin"}

@router.post("/admin/create")
def create_admin(
    request: CreateAdminRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal)
):
    # Only super admin can create admins
    if principal.role != RoleEnum.super_admin.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can create admins"
        )

    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new admin
    new_admin = User(
        username=request.username,
        email=request.email,
        password=hash_password(request.password),
        role_based=RoleEnum.admin.value,  # <- use role_based and .value
        domain_id=1  # or whichever domain you want to assign
)

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    return {
        "message": "Admin created successfully",
        "admin_id": new_admin.id
    }
@router.post("/super-admin/create")
def create_user_by_super_admin(
    request: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_db)
):
    if current_user.role != RoleEnum.super_admin.value:
        raise HTTPException(status_code=403, detail="Only super admins can create users/admins")
    
    if request.role not in [RoleEnum.admin.value, RoleEnum.user.value]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    new_user = User(
        username=request.username,
        email=request.email,
        password=hash_password(request.password),
        role_based=request.role,
        domain_id=request.domain_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": f"{request.role} created successfully", "user_id": new_user.id}

