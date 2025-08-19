"""
SQLAlchemy ORM entity definitions for Account and CustomField.

These entities use field-level encryption for sensitive data using SQLAlchemy-Utils'
StringEncryptedType and AES encryption. Entities are generated dynamically with a
provided encryption key.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_utils import StringEncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesGcmEngine

from database_settings import Base


def get_account_entity(key: str):
    """
    Dynamically generate the Account ORM entity class with encrypted fields.

    Args:
        key (str): Encryption key for field-level encryption.

    Returns:
        type: Account ORM class.
    """

    class Account(Base):
        """
        ORM model for the 'account' table.

        Attributes:
            id (int): Primary key.
            title (str): Encrypted account title.
            user_name (str): Encrypted user name.
            password (str): Encrypted password.
            url (str): Encrypted URL (optional).
            notes (str): Encrypted notes (optional).
            expiration_date (datetime): Encrypted expiration date (optional).
            creation_date (datetime): Creation timestamp.
            last_modification_date (datetime): Last modification timestamp.
            custom_fields (list): Relationship to CustomField.
        """

        __tablename__ = "account"

        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
        title: Mapped[str] = mapped_column(
            StringEncryptedType(String, key, AesGcmEngine, "pkcs5"),
            nullable=False,
        )
        user_name: Mapped[str] = mapped_column(
            StringEncryptedType(String, key, AesGcmEngine, "pkcs5"), nullable=False
        )
        password: Mapped[str] = mapped_column(
            StringEncryptedType(String, key, AesGcmEngine, "pkcs5"), nullable=False
        )
        url: Mapped[str] = mapped_column(
            StringEncryptedType(String, key, AesGcmEngine, "pkcs5"), nullable=True
        )
        notes: Mapped[str] = mapped_column(
            StringEncryptedType(String, key, AesGcmEngine, "pkcs5"), nullable=True
        )
        expiration_date: Mapped[datetime] = mapped_column(
            StringEncryptedType(DateTime, key, AesGcmEngine, "pkcs5"), nullable=True
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
    """
    Dynamically generate the CustomField ORM entity class with encrypted fields.

    Args:
        key (str): Encryption key for field-level encryption.

    Returns:
        type: CustomField ORM class.
    """

    class CustomField(Base):
        """
        ORM model for the 'custom_field' table.

        Attributes:
            id (int): Primary key.
            name (str): Encrypted custom field name.
            value (str): Encrypted custom field value.
            account_id (int): Foreign key to Account.
            creation_date (datetime): Creation timestamp.
            last_modification_date (datetime): Last modification timestamp.
            account (Account): Relationship to Account.
        """

        __tablename__ = "custom_field"

        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
        name: Mapped[str] = mapped_column(
            StringEncryptedType(String, key, AesGcmEngine, "pkcs5"), nullable=False
        )
        value: Mapped[str] = mapped_column(
            StringEncryptedType(String, key, AesGcmEngine, "pkcs5"), nullable=False
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
