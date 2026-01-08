
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid


class ResourceCreate(BaseModel):
    title: str
    content: Optional[str] = None
    category_code: str
    is_public: bool = False


class ResourceUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_public: Optional[bool] = None


class ResourceResponse(BaseModel):
    id: uuid.UUID
    title: str
    content: Optional[str]
    category_code: str
    owner_id: uuid.UUID
    is_public: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ResourceListResponse(BaseModel):
    total: int
    items: list[ResourceResponse]
