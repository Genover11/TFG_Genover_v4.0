

# src/ship_broker/api/routes/cargoes.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ...core.database import Cargo
from ...core.schemas import Cargo as CargoSchema
from ..dependencies import get_db

router = APIRouter()

@router.get("/cargoes/", response_model=List[CargoSchema])
def read_cargoes(
    skip: int = 0, 
    limit: int = 100, 
    cargo_type: Optional[str] = None,
    load_port: Optional[str] = None,
    discharge_port: Optional[str] = None,
    min_quantity: Optional[float] = None,
    max_quantity: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Read a list of cargoes with optional filters
    """
    query = db.query(Cargo)
    
    if cargo_type:
        query = query.filter(Cargo.cargo_type.ilike(f"%{cargo_type}%"))
    if load_port:
        query = query.filter(Cargo.load_port.ilike(f"%{load_port}%"))
    if discharge_port:
        query = query.filter(Cargo.discharge_port.ilike(f"%{discharge_port}%"))
    if min_quantity is not None:
        query = query.filter(Cargo.quantity >= min_quantity)
    if max_quantity is not None:
        query = query.filter(Cargo.quantity <= max_quantity)
    
    return query.offset(skip).limit(limit).all()

@router.get("/cargoes/{cargo_id}", response_model=CargoSchema)
def read_cargo(cargo_id: int, db: Session = Depends(get_db)):
    """
    Read a specific cargo by its ID
    """
    cargo = db.query(Cargo).filter(Cargo.id == cargo_id).first()
    if cargo is None:
        raise HTTPException(status_code=404, detail="Cargo not found")
    return cargo

@router.get("/cargoes/search/", response_model=List[CargoSchema])
def search_cargoes(
    q: str = Query(None, min_length=3),
    db: Session = Depends(get_db)
):
    """
    Search cargoes by various fields
    """
    if not q:
        return []
    
    return db.query(Cargo).filter(
        (Cargo.cargo_type.ilike(f"%{q}%")) |
        (Cargo.load_port.ilike(f"%{q}%")) |
        (Cargo.discharge_port.ilike(f"%{q}%")) |
        (Cargo.description.ilike(f"%{q}%"))
    ).all()