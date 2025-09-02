from sqlalchemy import Column, String, Date, DateTime, Enum, ForeignKey, Numeric, text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from app.db import Base
import enum
import uuid


def uuid4_str():
    return str(uuid.uuid4())


class TxType(str, enum.Enum):
    income = "income"
    expense = "expense"


class Frequency(str, enum.Enum):
    once = "once"
    weekly = "weekly"
    bi_weekly = "bi-weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"


class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4_str)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )

    accounts: Mapped[list["Account"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4_str)
    profile_id: Mapped[str] = mapped_column(
        String, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    starting_amount: Mapped[float] = mapped_column(
        Numeric(14, 2), nullable=False, default=0
    )
    start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)

    profile: Mapped["Profile"] = relationship(back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4_str)
    account_id: Mapped[str] = mapped_column(
        String, ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[TxType] = mapped_column(Enum(TxType), nullable=False)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    frequency: Mapped[Frequency] = mapped_column(
        Enum(Frequency), nullable=False, default=Frequency.once
    )
    date: Mapped[datetime | None] = mapped_column(
        Date, nullable=True
    )  # used when frequency=once
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )

    account: Mapped["Account"] = relationship(back_populates="transactions")
