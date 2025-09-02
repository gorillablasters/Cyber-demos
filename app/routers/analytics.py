from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Transaction
from datetime import date
from typing import Optional, List

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview/{profile_id}")
def get_overview(
    profile_id: str,
    db: Session = Depends(get_db),
    account_id: Optional[str] = None,
    tx_type: Optional[str] = Query(None, regex="^(income|expense)$"),
    category: Optional[str] = None,
    frequency: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """
    Return balances and totals with filters applied
    """
    q = (
        db.query(Transaction)
        .join(Transaction.account)
        .filter(Transaction.account.has(profile_id=profile_id))
    )

    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if tx_type:
        q = q.filter(Transaction.type == tx_type)
    if category:
        q = q.filter(Transaction.category == category)
    if frequency:
        q = q.filter(Transaction.frequency == frequency)
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)

    txs = q.all()

    income = sum(t.amount for t in txs if t.type == "income")
    expenses = sum(t.amount for t in txs if t.type == "expense")
    balance = income - expenses

    return {
        "income": income,
        "expenses": expenses,
        "balance": balance,
        "transactions": [t.to_dict() for t in txs],
    }


@router.get("/income/{profile_id}")
def get_income(
    profile_id: str,
    db: Session = Depends(get_db),
    account_id: Optional[str] = None,
    frequency: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    q = (
        db.query(Transaction)
        .join(Transaction.account)
        .filter(
            Transaction.account.has(profile_id=profile_id), Transaction.type == "income"
        )
    )

    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if frequency:
        q = q.filter(Transaction.frequency == frequency)
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)

    txs = q.all()
    return {
        "total_income": sum(t.amount for t in txs),
        "transactions": [t.to_dict() for t in txs],
    }


@router.get("/expenses/{profile_id}")
def get_expenses(
    profile_id: str,
    db: Session = Depends(get_db),
    account_id: Optional[str] = None,
    category: Optional[str] = None,
    frequency: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    q = (
        db.query(Transaction)
        .join(Transaction.account)
        .filter(
            Transaction.account.has(profile_id=profile_id),
            Transaction.type == "expense",
        )
    )

    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if category:
        q = q.filter(Transaction.category == category)
    if frequency:
        q = q.filter(Transaction.frequency == frequency)
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)

    txs = q.all()
    return {
        "total_expenses": sum(t.amount for t in txs),
        "transactions": [t.to_dict() for t in txs],
    }


@router.get("/trends/{profile_id}")
def get_trends(
    profile_id: str,
    db: Session = Depends(get_db),
    account_id: Optional[str] = None,
    frequency: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """
    Returns trends grouped by month (income vs expense)
    """
    from sqlalchemy import extract, func

    q = (
        db.query(
            extract("year", Transaction.date).label("year"),
            extract("month", Transaction.date).label("month"),
            Transaction.type,
            func.sum(Transaction.amount).label("total"),
        )
        .join(Transaction.account)
        .filter(Transaction.account.has(profile_id=profile_id))
    )

    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if frequency:
        q = q.filter(Transaction.frequency == frequency)
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)

    q = q.group_by("year", "month", Transaction.type).order_by("year", "month")

    results = q.all()

    return [
        {"year": int(r.year), "month": int(r.month), "type": r.type, "total": r.total}
        for r in results
    ]
