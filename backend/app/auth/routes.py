from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import timedelta

from app.DB.db import get_db
from app.auth.schemas import LoginRequest, TokenResponse
from app.Models.tables import User
from app.auth.utils import verify_password, create_access_token
from app.config import (
    ACCESS_TOKEN_EXPIRE_DELTA,
    SUPER_ADMIN_EMAIL,
    SUPER_ADMIN_PASSWORD,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    # Hardcoded Super Admin
    if data.username == SUPER_ADMIN_EMAIL and data.password == SUPER_ADMIN_PASSWORD:
        token = create_access_token(
            sub=SUPER_ADMIN_EMAIL,
            role="super_admin",
            domain_id=None,
            expires_delta=ACCESS_TOKEN_EXPIRE_DELTA,
        )
        return {
            "access_token": token,
            "role": "super_admin",
            "redirect": "/super-admin/dashboard",
        }

    # DB-backed users/admins
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        sub=user.username,
        role=user.role_based,
        domain_id=user.domain_id,
        expires_delta=ACCESS_TOKEN_EXPIRE_DELTA,
    )
    redirect = "/admin/dashboard" if user.role_based == "admin" else "/user/dashboard"
    return {"access_token": token, "role": user.role_based, "redirect": redirect}