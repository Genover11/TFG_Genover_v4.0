# src/ship_broker/api/routes/search.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ...core.database import Vessel, Cargo
from ...core.schemas import Vessel as VesselSchema, Cargo as CargoSchema
from ..dependencies import get_db

router = APIRouter()

@router.get("/search/vessels/", response_model=List[VesselSchema])
async def search_vessels(
    name: Optional[str] = None,
    vessel_type: Optional[str] = None,
    position: Optional[str] = None,
    min_dwt: Optional[float] = None,
    max_dwt: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Search vessels with filters"""
    query = db.query(Vessel)
    
    if name:
        query = query.filter(Vessel.name.ilike(f"%{name}%"))
    if vessel_type:
        query = query.filter(Vessel.vessel_type.ilike(f"%{vessel_type}%"))
    if position:
        query = query.filter(Vessel.position.ilike(f"%{position}%"))
    if min_dwt:
        query = query.filter(Vessel.dwt >= min_dwt)
    if max_dwt:
        query = query.filter(Vessel.dwt <= max_dwt)
        
    return query.all()

@router.get("/search/cargoes/", response_model=List[CargoSchema])
async def search_cargoes(
    cargo_type: Optional[str] = None,
    load_port: Optional[str] = None,
    discharge_port: Optional[str] = None,
    min_quantity: Optional[float] = None,
    max_quantity: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Search cargoes with filters"""
    query = db.query(Cargo)
    
    if cargo_type:
        query = query.filter(Cargo.cargo_type.ilike(f"%{cargo_type}%"))
    if load_port:
        query = query.filter(Cargo.load_port.ilike(f"%{load_port}%"))
    if discharge_port:
        query = query.filter(Cargo.discharge_port.ilike(f"%{discharge_port}%"))
    if min_quantity:
        query = query.filter(Cargo.quantity >= min_quantity)
    if max_quantity:
        query = query.filter(Cargo.quantity <= max_quantity)
        
    return query.all()