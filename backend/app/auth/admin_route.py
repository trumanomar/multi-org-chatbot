from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.DB.db import get_db
from app.auth.schemas import CreateUserRequest
from app.Models.tables import User, RoleEnum
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
