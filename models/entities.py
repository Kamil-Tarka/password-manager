from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_utils import StringEncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine

from database_settings import Base


def get_account_entity(key: str):
    class Account(Base):
        __tablename__ = "account"

        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
        title: Mapped[str] = mapped_column(
            StringEncryptedType(String, key, AesEngine, "pkcs5"),
            nullable=False,
        )
        user_name: Mapped[str] = mapped_column(
            StringEncryptedType(String, key, AesEngine, "pkcs5"), nullable=False
        )
        password: Mapped[str] = mapped_column(
            StringEncryptedType(String, key, AesEngine, "pkcs5"), nullable=False
        )
        url: Mapped[str] = mapped_column(
            StringEncryptedType(String, key, AesEngine, "pkcs5"), nullable=True
        )
        notes: Mapped[str] = mapped_column(
            StringEncryptedType(String, key, AesEngine, "pkcs5"), nullable=True
        )
        expiration_date: Mapped[datetime] = mapped_column(
            StringEncryptedType(DateTime, key, AesEngine, "pkcs5"), nullable=True
        )
        creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
        last_modification_date: Mapped[datetime] = mapped_column(
            DateTime, nullable=False
        )

        custom_fields = relationship(
            "CustomField", back_populates="account", cascade="all, delete-orphan"
        )

    return Account


def get_custom_field_entity(key: str):
    class CustomField(Base):
        __tablename__ = "custom_field"

        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
        name: Mapped[str] = mapped_column(
            StringEncryptedType(String, key, AesEngine, "pkcs5"), nullable=False
        )
        value: Mapped[str] = mapped_column(
            StringEncryptedType(String, key, AesEngine, "pkcs5"), nullable=False
        )
        account_id: Mapped[int] = mapped_column(
            Integer, ForeignKey("account.id"), nullable=False
        )
        creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
        last_modification_date: Mapped[datetime] = mapped_column(
            DateTime, nullable=False
        )

        account = relationship("Account", back_populates="custom_fields")

    return CustomField
