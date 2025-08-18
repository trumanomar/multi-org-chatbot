from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from enum import Enum
from datetime import datetime

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


class CreateSuperAdminRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    domain_name: str   
    

class CreateUserRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    domain_id:int

<<<<<<< HEAD
class CreateDomainRequest(BaseModel):
    name: str

class DeleteDocumentRequest(BaseModel):
    doc_id: int
    delete_vectors: bool = True

class DeleteDocumentResponse(BaseModel):
    message: str
    doc_id: int
    chunks_deleted: int
    vectors_deleted: Optional[int] = None
    
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

        
    
        
    
        
=======
class CreateUserRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
>>>>>>> 05c442592b57776dae5c4587a0e474f22d3cb1c8

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


