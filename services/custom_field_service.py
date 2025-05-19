from datetime import datetime
from typing import Type
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from exceptions.exceptions import NotFoundAccountException, NotFoundCustomFieldException
from models.models import CreateCustomFieldDTO, UpdateCustomFieldDTO
from services.account_service import AccountService


class CustomFieldService:

    def __init__(self, db: Session, CustomField: Type, Account: Type):
        self.db = db
        self.CustomField = CustomField
        self.Account = Account
        self._account_service = AccountService(db, Account)

    def get_by_id(self, id: int):
        custom_field = (
            self.db.query(self.CustomField).filter(self.CustomField.id == id).first()
        )
        if custom_field is None:
            raise NotFoundCustomFieldException(f"Custom field with id={id} not found")
        return custom_field

    def get_all(self):
        return self.db.query(self.CustomField).all()

    def create(self, create_custom_field_dto: CreateCustomFieldDTO):
        try:
            self._account_service.get_by_id(create_custom_field_dto.account_id)
        except NotFoundAccountException as e:
            print(f"Error: {e}")
            return None

        custom_field = self.CustomField(**create_custom_field_dto.model_dump())
        current_date = datetime.now(ZoneInfo("Europe/Warsaw"))
        custom_field.creation_date = current_date
        custom_field.last_modification_date = current_date
        self.db.add(custom_field)
        self.db.commit()
        self.db.refresh(custom_field)
        return custom_field

    def update(self, id: int, update_custom_field_dto: UpdateCustomFieldDTO):
        try:
            custom_field_to_update = self.get_by_id(id)
        except NotFoundCustomFieldException as e:
            print(f"Error: {e}")
            return None

        current_date = datetime.now(ZoneInfo("Europe/Warsaw"))
        if (
            update_custom_field_dto.name
            and custom_field_to_update.name != update_custom_field_dto.name
        ):
            custom_field_to_update.name = update_custom_field_dto.name
            custom_field_to_update.last_modification_date = current_date
        if (
            update_custom_field_dto.value
            and custom_field_to_update.value != update_custom_field_dto.value
        ):
            custom_field_to_update.value = update_custom_field_dto.value
            custom_field_to_update.last_modification_date = current_date
        self.db.commit()
        self.db.refresh(custom_field_to_update)
        return custom_field_to_update

    def delete(self, id: int):
        try:
            custom_field = self.get_by_id(id)
        except NotFoundCustomFieldException:
            return False

        self.db.delete(custom_field)
        self.db.commit()
        return True
