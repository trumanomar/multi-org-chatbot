from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.DB.db import get_db
from app.auth.schemas import ForgotPasswordRequest
from app.auth.dependencies import create_reset_token
from app.Models.tables import User


router=APIRouter(prefix="/user", tags=["user"])
@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = create_reset_token(user.username)

    # في الواقع: تبعته إيميل
    # للتجربة: هنرجعه في response
    return {"reset_token": token, "message": "Use this token to reset your password"}