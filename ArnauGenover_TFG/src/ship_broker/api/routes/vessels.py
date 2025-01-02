# src/ship_broker/api/routes/vessels.py


from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ...core.database import Vessel
from ...core.schemas import Vessel as VesselSchema, VesselCreate
from ...core.auction_service import AuctionService
from ..dependencies import get_db

router = APIRouter()

@router.get("/vessels/", response_model=List[VesselSchema])
def read_vessels(
    skip: int = 0,
    limit: int = 100,
    vessel_type: Optional[str] = None,
    position: Optional[str] = None,
    min_dwt: Optional[float] = None,
    max_dwt: Optional[float] = None,
    available_before: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Read a list of vessels with optional filters
    """
    query = db.query(Vessel)
    
    if vessel_type:
        query = query.filter(Vessel.vessel_type.ilike(f"%{vessel_type}%"))
    if position:
        query = query.filter(Vessel.position.ilike(f"%{position}%"))
    if min_dwt is not None:
        query = query.filter(Vessel.dwt >= min_dwt)
    if max_dwt is not None:
        query = query.filter(Vessel.dwt <= max_dwt)
    if available_before:
        query = query.filter(Vessel.open_date <= available_before)
    
    return query.offset(skip).limit(limit).all()

@router.get("/vessels/{vessel_id}", response_model=VesselSchema)
def read_vessel(vessel_id: int, db: Session = Depends(get_db)):
    """
    Read a specific vessel by its ID
    """
    vessel = db.query(Vessel).filter(Vessel.id == vessel_id).first()
    if vessel is None:
        raise HTTPException(status_code=404, detail="Vessel not found")
    return vessel

@router.get("/vessels/search/", response_model=List[VesselSchema])
def search_vessels(
    q: str = Query(None, min_length=3),
    db: Session = Depends(get_db)
):
    """
    Search vessels by various fields
    """
    if not q:
        return []
    
    return db.query(Vessel).filter(
        (Vessel.name.ilike(f"%{q}%")) |
        (Vessel.vessel_type.ilike(f"%{q}%")) |
        (Vessel.position.ilike(f"%{q}%")) |
        (Vessel.description.ilike(f"%{q}%"))
    ).all()

@router.post("/vessels/", response_model=VesselSchema)
async def create_vessel(vessel: VesselCreate, db: Session = Depends(get_db)):
    """Create a new vessel and start auction if ETA is provided"""
    db_vessel = Vessel(
        name=vessel.name,
        dwt=vessel.dwt,
        position=vessel.position,
        eta=vessel.eta,
        open_date=vessel.open_date,
        vessel_type=vessel.vessel_type,
        description=vessel.description
    )
    
    try:
        # Add vessel to database
        db.add(db_vessel)
        db.commit()
        db.refresh(db_vessel)
        
        # If vessel has ETA, create auction
        if db_vessel.eta:
            auction_service = AuctionService(db)
            auction_service.create_auction_for_vessel(db_vessel.id)
        
        return db_vessel
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/vessels/{vessel_id}", response_model=VesselSchema)
async def update_vessel(
    vessel_id: int,
    vessel: VesselCreate,
    db: Session = Depends(get_db)
):
    """Update a vessel and possibly start auction if ETA is added"""
    db_vessel = db.query(Vessel).filter(Vessel.id == vessel_id).first()
    if db_vessel is None:
        raise HTTPException(status_code=404, detail="Vessel not found")
    
    # Store old ETA
    old_eta = db_vessel.eta
    
    # Update all fields
    for var, value in vars(vessel).items():
        setattr(db_vessel, var, value)
    
    try:
        db.commit()
        db.refresh(db_vessel)
        
        # If ETA was added or changed, check for auction creation
        if db_vessel.eta and db_vessel.eta != old_eta:
            auction_service = AuctionService(db)
            auction_service.create_auction_for_vessel(db_vessel.id)
            
        return db_vessel
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/vessels/{vessel_id}")
async def delete_vessel(vessel_id: int, db: Session = Depends(get_db)):
    """Delete a vessel"""
    vessel = db.query(Vessel).filter(Vessel.id == vessel_id).first()
    if vessel is None:
        raise HTTPException(status_code=404, detail="Vessel not found")
        
    try:
        db.delete(vessel)
        db.commit()
        return {"message": "Vessel deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
