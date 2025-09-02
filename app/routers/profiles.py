from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db import get_db
from app import crud, schemas
from app.deps import profile_or_404

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("", response_model=List[schemas.ProfileOut])
def list_profiles(db: Session = Depends(get_db)):
    return crud.list_profiles(db)


@router.post("", response_model=schemas.ProfileOut)
def create_profile(body: schemas.ProfileCreate, db: Session = Depends(get_db)):
    return crud.create_profile(db, body)


@router.get("/{profile_id}", response_model=schemas.ProfileDetail)
def get_profile(
    profile: schemas.ProfileDetail = Depends(profile_or_404),
    db: Session = Depends(get_db),
):
    return crud.get_profile_detail(db, profile.id)


@router.put("/{profile_id}", response_model=schemas.ProfileOut)
def update_profile(
    body: schemas.ProfileUpdate,
    profile=Depends(profile_or_404),
    db: Session = Depends(get_db),
):
    return crud.update_profile(db, profile, body)


@router.delete("/{profile_id}")
def delete_profile(profile=Depends(profile_or_404), db: Session = Depends(get_db)):
    crud.delete_profile(db, profile)
    return {"status": "deleted"}
