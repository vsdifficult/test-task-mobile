from datetime import datetime
from sqlalchemy import Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
import uuid

from src.database.database import Base

class PermissionCache(Base):
    __tablename__ = "permission_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), 
        index=True
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resources.id"), 
        index=True
    )
    
    # Битовая маска разрешений для быстрой проверки
    # Биты: CREATE=1, READ=2, UPDATE=4, DELETE=8, EXECUTE=16, SHARE=32
    permissions_mask: Mapped[int] = mapped_column(Integer, default=0)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (
        Index('idx_permission_cache', 'user_id', 'resource_id'),
    )