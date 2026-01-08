from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

from src.database.models.enums import ActionType, PermissionScope


class PermissionGrant(BaseModel):
    user_id: uuid.UUID
    action: ActionType
    expires_at: Optional[datetime] = None


class PermissionRevoke(BaseModel):
    user_id: uuid.UUID
    action: ActionType


class RolePermissionCreate(BaseModel):
    role_code: str
    category_code: str
    action: ActionType
    scope: PermissionScope
    is_allowed: bool = True
    conditions: Optional[str] = None


class PermissionCheckResponse(BaseModel):
    allowed: bool
    reason: Optional[str] = None


class UserPermissionResponse(BaseModel):
    id: int
    resource_id: uuid.UUID
    action: ActionType
    is_allowed: bool
    granted_by: Optional[uuid.UUID]
    granted_at: datetime
    expires_at: Optional[datetime]
    
    class Config:
        from_attributes = True

