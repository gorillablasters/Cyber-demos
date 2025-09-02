from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date, datetime
from app.models import TxType, Frequency


class TransactionBase(BaseModel):
    name: str
    type: TxType
    amount: float
    frequency: Frequency = Frequency.once
    category: Optional[str] = None
    date: Optional[date] = None

    @field_validator("category")
    @classmethod
    def category_for_expense(cls, v, info):
        t: TxType = info.data.get("type")
        if t == TxType.expense and not v:
            raise ValueError("category is required for expenses")
        return v

    @field_validator("date")
    @classmethod
    def date_for_once(cls, v, info):
        f: Frequency = info.data.get("frequency")
        if f == Frequency.once and not v:
            raise ValueError("date is required when frequency is 'once'")
        return v


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[TxType] = None
    amount: Optional[float] = None
    frequency: Optional[Frequency] = None
    category: Optional[str] = None
    date: Optional[date] = None


class TransactionOut(TransactionBase):
    id: str
    account_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class AccountBase(BaseModel):
    name: str
    starting_amount: float = 0.0
    start_date: Optional[date] = None


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    starting_amount: Optional[float] = None
    start_date: Optional[date] = None


class AccountOut(AccountBase):
    id: str
    profile_id: str

    class Config:
        from_attributes = True


class ProfileBase(BaseModel):
    name: str


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(BaseModel):
    name: Optional[str] = None


class ProfileOut(ProfileBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProfileDetail(ProfileOut):
    accounts: List[AccountOut]
