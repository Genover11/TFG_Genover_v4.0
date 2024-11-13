# src/ship_broker/api/routes/vessels.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ...core.database import Vessel
from ...core.schemas import Vessel as VesselSchema
from ..dependencies import get_db

router = APIRouter()

@router.get("/vessels/", response_model=List[VesselSchema])
def read_vessels(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    vessels = db.query(Vessel).offset(skip).limit(limit).all()
    return vessels

@router.get("/vessels/{vessel_id}", response_model=VesselSchema)
def read_vessel(vessel_id: int, db: Session = Depends(get_db)):
    vessel = db.query(Vessel).filter(Vessel.id == vessel_id).first()
    if vessel is None:
        raise HTTPException(status_code=404, detail="Vessel not found")
    return vessel