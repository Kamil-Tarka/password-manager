"""
Data Transfer Objects (DTOs) for accounts and custom fields.

These Pydantic models are used for data validation and transfer between
the application layers (e.g., service and view).
"""

from datetime import datetime

from pydantic import BaseModel, Field


class CreateCustomFieldDTO(BaseModel):
    """
    DTO for creating a new custom field.

    Attributes:
        name (str): Name of the custom field (required, min length 1).
        value (str): Value of the custom field (required, min length 1).
        account_id (int): ID of the associated account (required, > 0).
    """

    name: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1)
    account_id: int = Field(..., gt=0)


class UpdateCustomFieldDTO(BaseModel):
    """
    DTO for updating an existing custom field.

    Attributes:
        name (str | None): New name for the custom field (optional).
        value (str | None): New value for the custom field (optional).
    """

    name: str | None = None
    value: str | None = None


class CreateAccountDTO(BaseModel):
    """
    DTO for creating a new account.

    Attributes:
        title (str): Title of the account (required, min length 1).
        user_name (str): User name for the account (required, min length 1).
        password (str): Password for the account (required, min length 1).
        url (str | None): URL associated with the account (optional).
        notes (str | None): Additional notes (optional).
        expiration_date (datetime | None): Expiration date (optional).
    """

    title: str = Field(..., min_length=1)
    user_name: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    url: str | None = None
    notes: str | None = None
    expiration_date: datetime | None = None


class UpdateAccountDTO(BaseModel):
    """
    DTO for updating an existing account.

    Attributes:
        title (str | None): New title (optional).
        user_name (str | None): New user name (optional).
        password (str | None): New password (optional).
        url (str | None): New URL (optional).
        notes (str | None): New notes (optional).
        expiration_date (datetime | None): New expiration date (optional).
    """

    title: str | None = None
    user_name: str | None = None
    password: str | None = None
    url: str | None = None
    notes: str | None = None
    expiration_date: datetime | None = None
