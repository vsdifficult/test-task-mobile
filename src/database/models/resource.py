import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, TYPE_CHECKING

from src.database.database import Base
from src.database.models.enums import ResourceType

if TYPE_CHECKING:
    from src.database.models.user import User
    from src.database.models.permission import UserPermission, RolePermission
    from src.database.models.audit import AuditLog


class ResourceCategory(Base):
    __tablename__ = "resource_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str] = mapped_column(String(50), unique=True)
    resource_type: Mapped[str] = mapped_column(SQLEnum(ResourceType))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("resource_categories.id"), 
        nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    resources: Mapped[List["Resource"]] = relationship(
        "Resource", 
        back_populates="category"
    )
    role_permissions: Mapped[List["RolePermission"]] = relationship(
        "RolePermission", 
        back_populates="category"
    )
    parent: Mapped["ResourceCategory"] = relationship(
        "ResourceCategory",
        remote_side=[id],
        backref="children"
    )


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    category_id: Mapped[int] = mapped_column(ForeignKey("resource_categories.id"))
    
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )
    
    category: Mapped["ResourceCategory"] = relationship(
        "ResourceCategory", 
        back_populates="resources"
    )
    owner: Mapped["User"] = relationship(
        "User", 
        back_populates="owned_resources",
        foreign_keys=[owner_id]
    )
    user_permissions: Mapped[List["UserPermission"]] = relationship(
        "UserPermission", 
        back_populates="resource"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", 
        back_populates="resource"
    )

    __table_args__ = (
        Index('idx_resource_owner', 'owner_id'),
        Index('idx_resource_category', 'category_id'),
    )