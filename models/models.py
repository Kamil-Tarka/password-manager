from datetime import datetime

from pydantic import BaseModel, Field


class CreateCustomFieldDTO(BaseModel):
    name: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1)
    account_id: int = Field(..., gt=0)


class UpdateCustomFieldDTO(BaseModel):
    name: str | None = None
    value: str | None = None


class CreateAccountDTO(BaseModel):
    title: str = Field(..., min_length=1)
    user_name: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    url: str | None = None
    notes: str | None = None
    expiration_date: datetime | None = None


class UpdateAccountDTO(BaseModel):
    title: str | None = None
    user_name: str | None = None
    password: str | None = None
    url: str | None = None
    notes: str | None = None
    expiration_date: datetime | None = None
