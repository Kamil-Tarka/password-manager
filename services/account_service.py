from datetime import datetime
from typing import Type
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from exceptions.exceptions import NotFoundAccountException
from models.models import CreateAccountDTO, UpdateAccountDTO


class AccountService:
    def __init__(self, db: Session, Account: Type):
        self.db = db
        self.Account = Account

    def get_by_id(self, id: int):
        account = self.db.query(self.Account).filter(self.Account.id == id).first()
        if account is None:
            raise NotFoundAccountException(f"Not found account with id={id}")
        return account

    def get_all(self):
        return self.db.query(self.Account).all()

    def create(self, create_account_dto: CreateAccountDTO):
        account = self.Account(**create_account_dto.model_dump())
        current_date = datetime.now(ZoneInfo("Europe/Warsaw"))
        account.creation_date = current_date
        account.last_modification_date = current_date
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def update(self, id: int, update_account_dto: UpdateAccountDTO):
        try:
            account = self.get_by_id(id)
        except NotFoundAccountException as e:
            print(f"Error: {e}")
            return None

        current_date = datetime.now(ZoneInfo("Europe/Warsaw"))
        if update_account_dto.title and account.title != update_account_dto.title:
            account.title = update_account_dto.title
            account.last_modification_date = current_date
        if (
            update_account_dto.user_name
            and account.user_name != update_account_dto.user_name
        ):
            account.user_name = update_account_dto.user_name
            account.last_modification_date = current_date
        if (
            update_account_dto.password
            and account.password != update_account_dto.password
        ):
            account.password = update_account_dto.password
            account.last_modification_date = current_date
        if update_account_dto.url and account.url != update_account_dto.url:
            account.url = update_account_dto.url
            account.last_modification_date = current_date
        if update_account_dto.notes and account.notes != update_account_dto.notes:
            account.notes = update_account_dto.notes
            account.last_modification_date = current_date
        if (
            update_account_dto.expiration_date
            and account.expiration_date != update_account_dto.expiration_date
        ):
            account.expiration_date = update_account_dto.expiration_date
            account.last_modification_date = current_date
        self.db.commit()
        self.db.refresh(account)
        return account

    def delete(self, id: int):
        try:
            account = self.get_by_id(id)
        except NotFoundAccountException as e:
            print(f"Error: {e}")
            return False

        self.db.delete(account)
        self.db.commit()
        return True
