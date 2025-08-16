from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.config import SECRET_KEY, ALGORITHM, SUPER_ADMIN_EMAIL
from app.DB.db import get_db
from app.Models.tables import User, RoleEnum
from typing import Optional

bearer_scheme = HTTPBearer(auto_error=False)

class Principal:
    def __init__(self, sub: str, role: str, domain_id: Optional[int]):
        self.sub = sub
        self.role = role
        self.domain_id = domain_id


def get_current_principal(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Principal:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = creds.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        role = payload.get("role")
        domain_id = payload.get("domain_id")
        if not sub or not role:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return Principal(sub=sub, role=role, domain_id=domain_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_super_admin(principal: Principal = Depends(get_current_principal)) -> Principal:
    if principal.role != RoleEnum.super_admin.value or principal.sub != SUPER_ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Super admin only")
    return principal


def require_admin(principal: Principal = Depends(get_current_principal)) -> Principal:
    if principal.role != RoleEnum.admin.value:
        raise HTTPException(status_code=403, detail="Admin only")
    return principal


def require_user(principal: Principal = Depends(get_current_principal)) -> Principal:
    if principal.role != RoleEnum.user.value:
        raise HTTPException(status_code=403, detail="User only")
    return principal


def require_admin_or_super(principal: Principal = Depends(get_current_principal)) -> Principal:
    if principal.role not in (RoleEnum.admin.value, RoleEnum.super_admin.value):
        raise HTTPException(status_code=403, detail="Admin or Super Admin required")
    return principal


def get_current_user_db(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Fetch the DB user for admin/user roles. Returns None for super_admin."""
    if principal.role == RoleEnum.super_admin.value:
        return None
    user = db.query(User).filter(User.username == principal.sub).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def enforce_same_domain_query(query, model, principal: Principal):
    """Apply domain filter for non-super roles."""
    if principal.role != RoleEnum.super_admin.value:
        return query.filter(model.domain_id == principal.domain_id)
    return query