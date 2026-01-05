from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database.database import Base

class BusinessElement(Base):
    __tablename__ = "business_elements"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True)

class AccessRule(Base):
    __tablename__ = "access_rules"

    role_id = mapped_column(ForeignKey("roles.id"), primary_key=True)
    element_id = mapped_column(ForeignKey("business_elements.id"), primary_key=True)

    read_permission: Mapped[bool] = mapped_column(Boolean, default=False)
    read_all_permission: Mapped[bool] = mapped_column(Boolean, default=False)

    create_permission: Mapped[bool] = mapped_column(Boolean, default=False)

    update_permission: Mapped[bool] = mapped_column(Boolean, default=False)
    update_all_permission: Mapped[bool] = mapped_column(Boolean, default=False)

    delete_permission: Mapped[bool] = mapped_column(Boolean, default=False)
    delete_all_permission: Mapped[bool] = mapped_column(Boolean, default=False)
