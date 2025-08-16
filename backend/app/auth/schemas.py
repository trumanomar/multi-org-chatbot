from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from enum import Enum

class RoleEnum(str, Enum):
    super_admin = "super_admin"
    admin = "admin"
    user = "user"

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: RoleEnum
    redirect: str

class RegisterAdmin(BaseModel):
    username: str
    password: str
    domain_name: str = Field(..., description="New or existing domain name")

class RegisterUser(BaseModel):
    username: str
    password: str

class DomainOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class UserOut(BaseModel):
    id: int
    username: str
    role: RoleEnum
    domain_id: Optional[int]
    class Config:
        from_attributes = True

class CreateAdminRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class CreateUserRequest(BaseModel):
    username: str
    email: EmailStr  # required
    password: str


