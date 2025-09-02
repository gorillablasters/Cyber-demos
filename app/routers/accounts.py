from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db import get_db
from app import crud, schemas
from app.deps import profile_or_404, account_or_404

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("/profile/{profile_id}", response_model=schemas.AccountOut)
def add_account(
    profile=Depends(profile_or_404),
    body: schemas.AccountCreate = None,
    db: Session = Depends(get_db),
):
    return crud.create_account(db, profile.id, body)


@router.put("/{account_id}", response_model=schemas.AccountOut)
def update_account(
    account=Depends(account_or_404),
    body: schemas.AccountUpdate = None,
    db: Session = Depends(get_db),
):
    return crud.update_account(db, account, body)


@router.delete("/{account_id}")
def delete_account(account=Depends(account_or_404), db: Session = Depends(get_db)):
    crud.delete_account(db, account)
    return {"status": "deleted"}
