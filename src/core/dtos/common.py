
from pydantic import BaseModel
from typing import Optional


class AuthResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    token: Optional[str] = None


class MessageResponse(BaseModel):
    success: bool
    message: str