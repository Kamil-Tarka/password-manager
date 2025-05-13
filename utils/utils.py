import contextlib
from typing import Generator

from sqlalchemy.orm import Session

from database_settings import Base, SessionLocal, engine
from models.entities import get_account_entity, get_custom_field_entity


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
