import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, TYPE_CHECKING

from src.database.database import Base

if TYPE_CHECKING:
    from src.database.models.resource import Resource
    from src.database.models.permission import UserPermission, RolePermission
    from src.database.models.audit import AuditLog


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    users: Mapped[List["User"]] = relationship("User", back_populates="department", foreign_keys="User.department_id")
    parent: Mapped["Department"] = relationship(
        "Department", 
        remote_side=[id], 
        backref="children"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id"), 
        nullable=True
    )
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    department: Mapped["Department"] = relationship(
        "Department", 
        back_populates="users",
        foreign_keys=[department_id]
    )
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary="user_roles",
        primaryjoin="User.id == foreign(UserRole.user_id)",
        secondaryjoin="Role.id == foreign(UserRole.role_id)",
        back_populates="users",
        lazy="selectin",
        viewonly=True
    )
    owned_resources: Mapped[List["Resource"]] = relationship(
        "Resource", 
        back_populates="owner",
        foreign_keys="Resource.owner_id"
    )
    personal_permissions: Mapped[List["UserPermission"]] = relationship(
        "UserPermission", 
        back_populates="user",
        foreign_keys="UserPermission.user_id"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", 
        back_populates="user",
        foreign_keys="AuditLog.user_id"
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    parent_role_id: Mapped[int | None] = mapped_column(
        ForeignKey("roles.id"), 
        nullable=True
    )
    priority: Mapped[int] = mapped_column(Integer, default=0)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    users: Mapped[List["User"]] = relationship(
        "User",
        secondary="user_roles",
        primaryjoin="Role.id == foreign(UserRole.role_id)",
        secondaryjoin="User.id == foreign(UserRole.user_id)",
        back_populates="roles",
        viewonly=True
    )
    permissions: Mapped[List["RolePermission"]] = relationship(
        "RolePermission", 
        back_populates="role"
    )
    parent_role: Mapped["Role"] = relationship(
        "Role", 
        remote_side=[id], 
        backref="child_roles"
    )


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), 
        primary_key=True
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id"), 
        primary_key=True
    )
    
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), 
        nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)