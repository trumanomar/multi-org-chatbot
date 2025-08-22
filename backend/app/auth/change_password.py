from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import timedelta

from app.DB.db import get_db
from app.auth.schemas import changePasswordRequest, TokenResponse
from app.auth.dependencies import get_current_principal, Principal
from app.Models.tables import User
from app.auth.utils import verify_password, create_access_token
from app.auth.utils import hash_password

router = APIRouter(prefix="/user", tags=["user"])

@router.post("/change-password", response_model=TokenResponse)
def change_password(
    data: changePasswordRequest, 
    db: Session = Depends(get_db), 
    principal: Principal = Depends(get_current_principal)
):
    # Verify current password
    user = db.query(User).filter(User.username == principal.sub).first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid current password")

    # Update password
    user.password = hash_password(data.new_password)
    db.commit()
    db.refresh(user)

    # Generate new access token
    token = create_access_token(
        sub=user.username,
        role=user.role_based,
        domain_id=user.domain_id,
        expires_delta=timedelta(minutes=15),  # Adjust as needed
    )
    return {
        "access_token": token,
        "role": user.role_based,
        "redirect": "/user/dashboard" if user.role_based != "admin" else "/admin/dashboard",
    }
    