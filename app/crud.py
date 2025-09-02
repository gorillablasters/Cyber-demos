from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, case
from typing import Optional, Iterable
from datetime import date
from app import models, schemas


def list_profiles(db: Session) -> list[models.Profile]:
    return db.execute(select(models.Profile)).scalars().all()


def get_profile(db: Session, profile_id: str) -> Optional[models.Profile]:
    return db.get(models.Profile, profile_id)


def get_profile_detail(db: Session, profile_id: str) -> Optional[models.Profile]:
    stmt = (
        select(models.Profile)
        .options(joinedload(models.Profile.accounts))
        .where(models.Profile.id == profile_id)
    )
    return db.execute(stmt).unique().scalar_one_or_none()


def create_profile(db: Session, data: schemas.ProfileCreate) -> models.Profile:
    obj = models.Profile(name=data.name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_profile(
    db: Session, profile: models.Profile, data: schemas.ProfileUpdate
) -> models.Profile:
    if data.name is not None:
        profile.name = data.name
    db.commit()
    db.refresh(profile)
    return profile


def delete_profile(db: Session, profile: models.Profile) -> None:
    db.delete(profile)
    db.commit()


def create_account(
    db: Session, profile_id: str, data: schemas.AccountCreate
) -> models.Account:
    obj = models.Account(profile_id=profile_id, **data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_account(db: Session, account_id: str) -> Optional[models.Account]:
    return db.get(models.Account, account_id)


def update_account(
    db: Session, account: models.Account, data: schemas.AccountUpdate
) -> models.Account:
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(account, f, v)
    db.commit()
    db.refresh(account)
    return account


def delete_account(db: Session, account: models.Account) -> None:
    db.delete(account)
    db.commit()


def create_transaction(
    db: Session, account_id: str, data: schemas.TransactionCreate
) -> models.Transaction:
    obj = models.Transaction(account_id=account_id, **data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_transaction(db: Session, tx_id: str) -> Optional[models.Transaction]:
    return db.get(models.Transaction, tx_id)


def update_transaction(
    db: Session, tx: models.Transaction, data: schemas.TransactionUpdate
) -> models.Transaction:
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(tx, f, v)
    db.commit()
    db.refresh(tx)
    return tx


def delete_transaction(db: Session, tx: models.Transaction) -> None:
    db.delete(tx)
    db.commit()


def totals_for_profile(db: Session, profile_id: str):
    income_sum = (
        db.scalar(
            select(func.coalesce(func.sum(models.Transaction.amount), 0))
            .join(models.Account, models.Account.id == models.Transaction.account_id)
            .where(
                models.Account.profile_id == profile_id,
                models.Transaction.type == models.TxType.income,
            )
        )
        or 0
    )
    expense_sum = (
        db.scalar(
            select(func.coalesce(func.sum(models.Transaction.amount), 0))
            .join(models.Account, models.Account.id == models.Transaction.account_id)
            .where(
                models.Account.profile_id == profile_id,
                models.Transaction.type == models.TxType.expense,
            )
        )
        or 0
    )
    starting = (
        db.scalar(
            select(func.coalesce(func.sum(models.Account.starting_amount), 0)).where(
                models.Account.profile_id == profile_id
            )
        )
        or 0
    )
    return {
        "starting_total": float(starting),
        "income_total": float(income_sum),
        "expense_total": float(expense_sum),
        "net": float(starting + income_sum - expense_sum),
    }


def expense_breakdown_by_category(db: Session, profile_id: str):
    rows = db.execute(
        select(models.Transaction.category, func.sum(models.Transaction.amount))
        .join(models.Account, models.Account.id == models.Transaction.account_id)
        .where(
            models.Account.profile_id == profile_id,
            models.Transaction.type == models.TxType.expense,
        )
        .group_by(models.Transaction.category)
    ).all()
    return [{"category": c or "Uncategorized", "amount": float(a)} for c, a in rows]


def income_vs_expense_timeseries(
    db: Session, profile_id: str, date_from: date | None, date_to: date | None
):
    q = (
        select(
            models.Transaction.type,
            models.Transaction.date,
            func.sum(models.Transaction.amount),
        )
        .join(models.Account, models.Account.id == models.Transaction.account_id)
        .where(
            models.Account.profile_id == profile_id,
            models.Transaction.frequency == models.Frequency.once,
        )
        .group_by(models.Transaction.type, models.Transaction.date)
        .order_by(models.Transaction.date.asc())
    )
    if date_from:
        q = q.where(models.Transaction.date >= date_from)
    if date_to:
        q = q.where(models.Transaction.date <= date_to)
    rows = db.execute(q).all()
    series = {}
    for t, d, amt in rows:
        if not d:
            continue
        day = d.isoformat()
        series.setdefault(day, {"date": day, "income": 0.0, "expense": 0.0})
        series[day]["income" if t == models.TxType.income else "expense"] += float(amt)
    return sorted(series.values(), key=lambda r: r["date"])
