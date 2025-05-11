from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from exceptions.exceptions import DatabaseSettingsException


class DatabaseSettings:
    def __init__(self, path_to_db: str):
        SQLALCHEMY_DATABASE_URL = f"sqlite:///{path_to_db}"
        self._engine = create_engine(
            SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
        )
        self._SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self._Base = declarative_base()

    @property
    def SessionLocal(self):
        if self._SessionLocal is None:
            raise DatabaseSettingsException(
                "SessionLocal is not initialized. Please check the database settings."
            )
        return self._SessionLocal()

    @property
    def engine(self):
        if self._engine is None:
            raise DatabaseSettingsException(
                "Engine is not initialized. Please check the database settings."
            )
        return self._engine

    @property
    def Base(self):
        if self._Base is None:
            raise DatabaseSettingsException(
                "Base is not initialized. Please check the database settings."
            )
        return self._Base
