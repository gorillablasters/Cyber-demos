from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app import crud, models


def profile_or_404(profile_id: str, db: Session = Depends(get_db)) -> models.Profile:
    p = crud.get_profile(db, profile_id)
    if not p:
        raise HTTPException(404, "Profile not found")
    return p


def account_or_404(account_id: str, db: Session = Depends(get_db)) -> models.Account:
    a = crud.get_account(db, account_id)
    if not a:
        raise HTTPException(404, "Account not found")
    return a


def tx_or_404(tx_id: str, db: Session = Depends(get_db)) -> models.Transaction:
    t = crud.get_transaction(db, tx_id)
    if not t:
        raise HTTPException(404, "Transaction not found")
    return t
