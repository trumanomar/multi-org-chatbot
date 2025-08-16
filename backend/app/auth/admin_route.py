from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.DB.db import get_db
from app.auth.schemas import CreateUserRequest
from app.Models.tables import User, RoleEnum
from app.auth.utils import hash_password
from app.auth.dependencies import get_current_user_db

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/create_user")
def create_user(
    request: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_db)
):
    # Only admins and super_admins can create users
    if current_user.role_based not in [RoleEnum.admin.value, RoleEnum.super_admin.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins or super admins can create users"
        )

    # Check if username already exists
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    new_user = User(
        username=request.username,
        email=request.email,
        password=hash_password(request.password),
        role_based=RoleEnum.user.value,
        domain_id=current_user.domain_id  # user inherits admin's domain
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created successfully", "user_id": new_user.id}
