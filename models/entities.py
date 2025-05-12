import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database_settings import Base


class Account(Base):
    __tablename__ = "account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    user_name: Mapped[str] = mapped_column(String, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=True)
    notes: Mapped[str] = mapped_column(String, nullable=True)
    expiration_date: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)
    creation_date: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    last_modification_date: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False
    )

    custom_fields: Mapped[list["CustomField"]] = relationship(
        "CustomField", back_populates="account", cascade="all, delete-orphan"
    )


class CustomField(Base):
    __tablename__ = "custom_field"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("account.id"), nullable=False
    )
    creation_date: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    last_modification_date: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False
    )

    account: Mapped[Account] = relationship("Account", back_populates="custom_fields")
