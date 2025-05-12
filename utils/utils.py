from typing import Generator

from sqlalchemy.orm import Session

from database_settings import SessionLocal


def get_db_session() -> Generator[Session, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
