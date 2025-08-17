from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from typing import Optional
from app.config import SECRET_KEY, ALGORITHM

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(*, sub: str, role: str, domain_id: Optional[int], expires_delta: timedelta) -> str:
    to_encode = {
        "sub": sub,
        "role": role,
        "domain_id": domain_id,
        "exp": datetime.utcnow() + expires_delta,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)