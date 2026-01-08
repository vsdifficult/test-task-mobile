from pydantic import BaseModel, EmailStr
from typing import Optional


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    again_password: str
    first_name: str
    last_name: str
    department_id: Optional[int] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    department_id: Optional[int] = None


class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    department_id: Optional[int]
    is_active: bool
    
    class Config:
        from_attributes = True



