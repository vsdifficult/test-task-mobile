import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Text, 
    Enum as SQLEnum, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from src.database.database import Base
from src.database.models.enums import ActionType, PermissionScope

if TYPE_CHECKING:
    from src.database.models.user import User, Role
    from src.database.models.resource import Resource, ResourceCategory


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("resource_categories.id"))
    
    action: Mapped[str] = mapped_column(SQLEnum(ActionType))
    scope: Mapped[str] = mapped_column(SQLEnum(PermissionScope))
    
    conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    is_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    role: Mapped["Role"] = relationship("Role", back_populates="permissions")
    category: Mapped["ResourceCategory"] = relationship(
        "ResourceCategory", 
        back_populates="role_permissions"
    )

    __table_args__ = (
        Index('idx_role_permission', 'role_id', 'category_id', 'action'),
    )


class UserPermission(Base):
    __tablename__ = "user_permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    resource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resources.id"))
    
    action: Mapped[str] = mapped_column(SQLEnum(ActionType))
    
    is_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), 
        nullable=True
    )
    granted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(
        "User", 
        foreign_keys=[user_id], 
        back_populates="personal_permissions"
    )
    resource: Mapped["Resource"] = relationship(
        "Resource", 
        back_populates="user_permissions"
    )

    __table_args__ = (
        Index('idx_user_permission', 'user_id', 'resource_id', 'action'),
    )