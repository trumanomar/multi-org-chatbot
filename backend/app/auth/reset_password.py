from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import timedelta

from app.DB.db import get_db
from app.auth.schemas import ResetPasswordRequest
from app.auth.dependencies import verify_reset_token
from app.Models.tables import User
from app.auth.utils import hash_password
router = APIRouter(prefix="/user", tags=["user"])

@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    username = verify_reset_token(data.token)
    if not username:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password = hash_password(data.new_password)
    db.commit()
    db.refresh(user)

    return {"message": "Password reset successful"}