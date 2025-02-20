# src/ship_broker/api/routes/vessels.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from ...core.database import Vessel
from ...core.schemas import Vessel as VesselSchema
from ...core.vessel_tracker import tracker
from ..dependencies import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("", response_model=List[VesselSchema])
@router.get("/", response_model=List[VesselSchema])  # Adding both paths to handle both cases
async def get_vessels(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all vessels"""
    try:
        vessels = db.query(Vessel).offset(skip).limit(limit).all()
        return vessels
    except Exception as e:
        logger.error(f"Error getting vessels: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{vessel_id}", response_model=VesselSchema)
async def get_vessel(vessel_id: int, db: Session = Depends(get_db)):
    """Get a specific vessel"""
    vessel = db.query(Vessel).filter(Vessel.id == vessel_id).first()
    if vessel is None:
        raise HTTPException(status_code=404, detail="Vessel not found")
    return vessel

# Rest of your vessel routes...