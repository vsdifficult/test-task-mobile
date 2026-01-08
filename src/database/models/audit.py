import uuid
from datetime import datetime
from sqlalchemy import (
    String, Boolean, DateTime, ForeignKey, Text, 
    Enum as SQLEnum, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from src.database.database import Base
from src.database.models.enums import ActionType

if TYPE_CHECKING:
    from src.database.models.user import User
    from src.database.models.resource import Resource


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resources.id"), 
        nullable=True
    )
    
    action: Mapped[str] = mapped_column(SQLEnum(ActionType))
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        index=True
    )

    user: Mapped["User"] = relationship("User", back_populates="audit_logs")
    resource: Mapped["Resource"] = relationship("Resource", back_populates="audit_logs")

    __table_args__ = (
        Index('idx_audit_user_time', 'user_id', 'created_at'),
        Index('idx_audit_resource', 'resource_id', 'created_at'),
    )

