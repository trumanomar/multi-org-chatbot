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
    domain_id:int

class CreateUserRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "user1",
                "email": "user1@example.com",
                "password": "user1234"
            }
        }
    }
    
class CreateDomainRequest(BaseModel):
    name: str = Field(..., min_length=1) 
    active: bool = True


class FeedbackCreate(BaseModel):
    content: str
    rating: int
    question: str
    


class FeedbackResponse(BaseModel):
    id: int
    user_id: int
    content: str
    rating: int
    question: str

    class Config:
        orm_mode = True
class changePasswordRequest(BaseModel):
    password: str
    new_password: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "password": "current_password",
                "new_password": "new_password1234"
            }
        }
    }  
class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str  
class ForgotPasswordRequest(BaseModel):
    username: str    

