"""
Utility functions for the Password Manager application.

This module provides helpers for database session management, password generation,
password strength checking, clipboard operations, and database creation.
"""

import contextlib
import hashlib
import os
import re
import secrets
import string
from typing import Generator

import pyperclip
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, Session, declarative_base, mapped_column
from sqlalchemy_utils import StringEncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import (
    AesGcmEngine,
    InvalidCiphertextError,
)

from database_settings import Base, SessionLocal, engine
from models.entities import get_account_entity, get_custom_field_entity
from services.account_service import AccountService


@contextlib.contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for SQLAlchemy database session.
    Yields:
        Session: SQLAlchemy session object.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_database(secret_key: str):
    """
    Create database tables and return Account and CustomField ORM classes
    using the provided encryption key.

    Args:
        secret_key (str): The encryption key for field encryption.

    Returns:
        tuple: (Account, CustomField) ORM classes.
    """
    Account = get_account_entity(secret_key)
    CustomField = get_custom_field_entity(secret_key)

    Base.metadata.create_all(bind=engine)

    return Account, CustomField


def check_if_db_exists() -> bool:
    """
    Check if the database exists.

    Returns:
        bool: True if the database exists, False otherwise.
    """
    try:
        with open("passwords.db", "rb") as f:
            return True
    except FileNotFoundError:
        return False


def check_if_db_is_empty(account_service: AccountService) -> bool:
    """
    Check if the database contains any accounts.

    Args:
        account_service (AccountService): Service for account operations.

    Returns:
        bool: True if empty, False otherwise.
    """
    result = account_service.check_if_any_account()
    return result


def create_salt() -> bytes:
    """Generate new 16-byte salt for passwordhashing and save it to file."""
    salt = os.urandom(16)
    with open("salt.bin", "wb") as f:
        f.write(salt)
    return salt


def load_salt() -> bytes:
    """Load salt from file."""
    try:
        with open("salt.bin", "rb") as f:
            return f.read()
    except FileNotFoundError:
        return None  # type: ignore


def derive_key(password: str, salt: bytes) -> bytes:
    """
    Generate 32-byte key using PBKDF2-HMAC-SHA256.
    """
    iterations = 600000
    key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations, dklen=32
    )
    return key


def is_key_valid(encryption_key: str) -> bool:
    """
    Check if the provided secret key is valid by attempting to fetch accounts.

    Args:
        account_service (AccountService): Service for account operations.

    Returns:
        bool: True if the key is valid, otherwise False.
    """
    TempBase = declarative_base()

    class TempAccount(TempBase):
        __tablename__ = "account"
        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
        title: Mapped[str] = mapped_column(
            StringEncryptedType(String, encryption_key, AesGcmEngine, "pkcs5")
        )

    db = SessionLocal()
    try:
        db.query(TempAccount).first()

        return True
    except InvalidCiphertextError:
        return False
    except Exception:
        return False
    finally:
        db.close()


def check_password_strength(password: str) -> str:
    """
    Evaluate the strength of a password.

    Args:
        password (str): The password to check.

    Returns:
        str: "Weak", "Moderate", or "Strong".
    """
    if len(password) < 8:
        return "Weak"

    has_upper = bool(re.search(r"[A-Z]", password))
    has_lower = bool(re.search(r"[a-z]", password))
    has_digit = bool(re.search(r"\d", password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))

    if all([has_upper, has_lower, has_digit, has_special]):
        return "Strong"
    elif (
        all([has_upper, has_lower])
        or all([has_upper, has_digit])
        or all([has_upper, has_special])
        or all([has_lower, has_digit])
        or all([has_lower, has_special])
        or all([has_digit, has_special])
    ):
        return "Moderate"
    else:
        return "Weak"


def coppy_to_clipboard(text: str):
    """
    Copy the provided text to the system clipboard.

    Args:
        text (str): The text to copy.
    """
    pyperclip.copy(text)


def generate_password(
    length: int,
    use_digits: bool,
    use_uppercase: bool,
    use_special: bool,
) -> str:
    """
    Generate a random password with the specified options.

    Args:
        length (int): Length of the password.
        use_digits (bool): Include digits.
        use_uppercase (bool): Include uppercase letters.
        use_special (bool): Include special characters.

    Returns:
        str: The generated password.

    Raises:
        ValueError: If length < 1 or no character types are selected.
    """

    if length < 1:
        raise ValueError("Password length must be at least 1")

    character_pool = string.ascii_lowercase
    if use_digits:
        character_pool += string.digits
    if use_uppercase:
        character_pool += string.ascii_uppercase
    if use_special:
        character_pool += string.punctuation

    if not character_pool:
        raise ValueError("At least one character type must be selected")

    password = "".join(secrets.choice(character_pool) for _ in range(length))
    return password
