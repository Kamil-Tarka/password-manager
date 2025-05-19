import contextlib
import random
import re
import string
from typing import Generator

import pyperclip
from sqlalchemy.orm import Session

from database_settings import Base, SessionLocal, engine
from models.entities import get_account_entity, get_custom_field_entity
from services.account_service import AccountService


@contextlib.contextmanager
def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_database(secret_key: str):

    Account = get_account_entity(secret_key)
    CustomField = get_custom_field_entity(secret_key)

    Base.metadata.create_all(bind=engine)

    return Account, CustomField


def check_if_db_is_empty(account_service: AccountService) -> bool:
    result = len(account_service.get_all())
    return result == 0


def check_secret_key(account_service: AccountService) -> bool:
    account_service.get_all()
    return True


def check_password_strength(password: str) -> str:
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
    pyperclip.copy(text)


def generate_password(
    length: int,
    use_digits: bool,
    use_uppercase: bool,
    use_special: bool,
) -> str:

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

    password = "".join(random.choice(character_pool) for _ in range(length))
    return password
