# src/ship_broker/api/routes/cargoes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from ...core.database import Cargo
from ...core.schemas import CargoCreate, CargoResponse
from ...core.cargo_tracker import CargoTracker
from ..dependencies import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/cargoes/", response_model=List[CargoResponse])
async def get_cargoes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all cargoes with pagination"""
    try:
        cargoes = db.query(Cargo).offset(skip).limit(limit).all()
        return cargoes
    except Exception as e:
        logger.error(f"Error getting cargoes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cargoes/{cargo_id}", response_model=CargoResponse)
async def get_cargo(cargo_id: int, db: Session = Depends(get_db)):
    """Get a specific cargo by ID"""
    cargo = db.query(Cargo).filter(Cargo.id == cargo_id).first()
    if cargo is None:
        raise HTTPException(status_code=404, detail="Cargo not found")
    return cargo

@router.post("/cargoes/", response_model=CargoResponse)
async def create_cargo(
    cargo: CargoCreate,
    db: Session = Depends(get_db)
):
    """Create a new cargo"""
    try:
        db_cargo = Cargo(
            cargo_type=cargo.cargo_type,
            quantity=cargo.quantity,
            load_port=cargo.load_port,
            discharge_port=cargo.discharge_port,
            laycan_start=cargo.laycan_start,
            laycan_end=cargo.laycan_end,
            description=cargo.description,
            rate=cargo.rate
        )
        db.add(db_cargo)
        db.commit()
        db.refresh(db_cargo)
        return db_cargo
    except Exception as e:
        logger.error(f"Error creating cargo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/cargoes/{cargo_id}", response_model=CargoResponse)
async def update_cargo(
    cargo_id: int,
    cargo: CargoCreate,
    db: Session = Depends(get_db)
):
    """Update a cargo"""
    try:
        db_cargo = db.query(Cargo).filter(Cargo.id == cargo_id).first()
        if db_cargo is None:
            raise HTTPException(status_code=404, detail="Cargo not found")
            
        for var, value in vars(cargo).items():
            setattr(db_cargo, var, value)
        
        db_cargo.last_updated = datetime.now()
        db.commit()
        db.refresh(db_cargo)
        return db_cargo
    except Exception as e:
        logger.error(f"Error updating cargo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cargoes/{cargo_id}")
async def delete_cargo(cargo_id: int, db: Session = Depends(get_db)):
    """Delete a cargo"""
    try:
        db_cargo = db.query(Cargo).filter(Cargo.id == cargo_id).first()
        if db_cargo is None:
            raise HTTPException(status_code=404, detail="Cargo not found")
            
        db.delete(db_cargo)
        db.commit()
        return {"message": "Cargo deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting cargo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))