import uuid
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from src.database.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str]
    first_name: Mapped[str]
    last_name: Mapped[str]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    roles = relationship("Role", secondary="user_roles", lazy="selectin")

class Role(Base): 

    __tablename__ = "roles" 

    id: Mapped[int] = mapped_column(primary_key=True) 
    name: Mapped[str] = mapped_column(String, unique=True) 


class UserRole(Base): 

    __tablename__ = "user_roles" 

    user_id = mapped_column(ForeignKey("users.id"), primary_key=True)
    role_id = mapped_column(ForeignKey("roles.id"), primary_key=True) 


