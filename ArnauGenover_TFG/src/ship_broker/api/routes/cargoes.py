# api/routes/cargoes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ...core.database import Cargo
from ...core.schemas import Cargo as CargoSchema
from ..dependencies import get_db

router = APIRouter()

@router.get("/cargoes/", response_model=List[CargoSchema])
def read_cargoes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    cargoes = db.query(Cargo).offset(skip).limit(limit).all()
    return cargoes

@router.get("/cargoes/{cargo_id}", response_model=CargoSchema)
def read_cargo(cargo_id: int, db: Session = Depends(get_db)):
    cargo = db.query(Cargo).filter(Cargo.id == cargo_id).first()
    if cargo is None:
        raise HTTPException(status_code=404, detail="Cargo not found")
    return cargo