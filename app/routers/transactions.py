from fastapi import APIRouter, Depends, UploadFile, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db import get_db
from app import crud, schemas
from app.deps import account_or_404, tx_or_404
from app.utils import parse_csv_transactions

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/account/{account_id}", response_model=schemas.TransactionOut)
def add_transaction(
    account=Depends(account_or_404),
    body: schemas.TransactionCreate = None,
    db: Session = Depends(get_db),
):
    return crud.create_transaction(db, account.id, body)


@router.put("/{tx_id}", response_model=schemas.TransactionOut)
def update_transaction(
    tx=Depends(tx_or_404),
    body: schemas.TransactionUpdate = None,
    db: Session = Depends(get_db),
):
    return crud.update_transaction(db, tx, body)


@router.delete("/{tx_id}")
def delete_transaction(tx=Depends(tx_or_404), db: Session = Depends(get_db)):
    crud.delete_transaction(db, tx)
    return {"status": "deleted"}


@router.post("/import/{account_id}")
async def import_csv(
    account=Depends(account_or_404),
    file: UploadFile = None,
    db: Session = Depends(get_db),
):
    if not file or not file.filename.endswith(".csv"):
        raise HTTPException(400, "Please upload a CSV file")
    content = (await file.read()).decode("utf-8", errors="ignore")
    rows = parse_csv_transactions(content)
    for r in rows:
        crud.create_transaction(db, account.id, schemas.TransactionCreate(**r))
    return {"imported": len(rows)}
