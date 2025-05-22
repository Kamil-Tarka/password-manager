"""
CustomFieldService provides CRUD operations for custom fields associated with accounts.

This service ensures that custom fields are always linked to valid accounts,
handles creation and update timestamps, and raises exceptions for not found resources.
"""

from datetime import datetime
from typing import Type
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from exceptions.exceptions import NotFoundAccountException, NotFoundCustomFieldException
from models.models import CreateCustomFieldDTO, UpdateCustomFieldDTO
from services.account_service import AccountService


class CustomFieldService:
    """
    Service class for managing custom fields in the database.
    """

    def __init__(self, db: Session, CustomField: Type, Account: Type):
        """
        Initialize the service with database session and ORM models.

        Args:
            db (Session): SQLAlchemy session.
            CustomField (Type): ORM class for custom fields.
            Account (Type): ORM class for accounts.
        """
        self.db = db
        self.CustomField = CustomField
        self.Account = Account
        self._account_service = AccountService(db, Account)

    def get_by_id(self, id: int):
        """
        Retrieve a custom field by its ID.

        Args:
            id (int): Custom field ID.

        Returns:
            CustomField: The custom field object.

        Raises:
            NotFoundCustomFieldException: If not found.
        """
        custom_field = (
            self.db.query(self.CustomField).filter(self.CustomField.id == id).first()
        )
        if custom_field is None:
            raise NotFoundCustomFieldException(f"Custom field with id={id} not found")
        return custom_field

    def get_all(self):
        """
        Retrieve all custom fields.

        Returns:
            list: List of all custom field objects.
        """
        return self.db.query(self.CustomField).all()

    def create(self, create_custom_field_dto: CreateCustomFieldDTO):
        """
        Create a new custom field for an account.

        Args:
            create_custom_field_dto (CreateCustomFieldDTO): Data for the new custom field.

        Returns:
            CustomField or None: The created custom field, or None if account not found.
        """
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
        """
        Update an existing custom field.

        Args:
            id (int): Custom field ID.
            update_custom_field_dto (UpdateCustomFieldDTO): Data to update.

        Returns:
            CustomField or None: The updated custom field, or None if not found.
        """
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
        """
        Delete a custom field by its ID.

        Args:
            id (int): Custom field ID.

        Returns:
            bool: True if deleted, False if not found.
        """
        try:
            custom_field = self.get_by_id(id)
        except NotFoundCustomFieldException:
            return False

        self.db.delete(custom_field)
        self.db.commit()
        return True
        return True
