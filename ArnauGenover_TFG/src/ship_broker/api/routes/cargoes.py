# src/ship_broker/api/routes/cargoes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime
import logging

from ...core.database import Cargo, Vessel
from ...core.schemas import CargoCreate, CargoResponse
from ...core.cargo_tracker import CargoTracker
from ...core.vessel_tracker import tracker
from ..dependencies import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/cargoes", response_model=List[CargoResponse])
@router.get("/cargoes/", response_model=List[CargoResponse])
async def get_cargoes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all cargoes with pagination"""
    try:
        cargoes = db.query(Cargo).order_by(Cargo.created_at.desc()).offset(skip).limit(limit).all()
        return cargoes
    except Exception as e:
        logger.error(f"Error getting cargoes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cargoes", response_model=CargoResponse)
@router.post("/cargoes/", response_model=CargoResponse)
async def create_cargo(cargo: CargoCreate, db: Session = Depends(get_db)):
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
        db.rollback()
        logger.error(f"Error creating cargo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cargoes/match/{cargo_id}/vessels", response_model=List[Dict])
async def get_matching_vessels(cargo_id: int, db: Session = Depends(get_db)):
    """Get vessels that match a specific cargo"""
    try:
        cargo = db.query(Cargo).filter(Cargo.id == cargo_id).first()
        if not cargo:
            raise HTTPException(status_code=404, detail="Cargo not found")

        # Get live vessels from tracker
        if not tracker.vessels_cache:
            return []

        matching_vessels = []
        for vessel in tracker.vessels_cache.values():
            if vessel.get('is_mock', True):
                continue

            # Calculate match score based on vessel properties
            score = 0.0
            reason = []

            # Location matching (40% of score)
            if cargo.load_port:
                port_coords = tracker._get_port_coordinates(cargo.load_port)
                if port_coords and vessel.get('lat') and vessel.get('lon'):
                    distance = tracker._calculate_distance(
                        port_coords['lat'],
                        port_coords['lon'],
                        vessel['lat'],
                        vessel['lon']
                    )
                    if distance <= 100:
                        score += 0.4
                        reason.append(f"Close to loading port ({distance:.0f} nm)")
                    elif distance <= 300:
                        score += 0.2
                        reason.append(f"Within range of loading port ({distance:.0f} nm)")

            # Type matching (30% of score)
            vessel_type = vessel.get('type', '').lower()
            cargo_type = cargo.cargo_type.lower()
            if ('bulk' in vessel_type and any(t in cargo_type for t in ['coal', 'ore', 'clinker'])):
                score += 0.3
                reason.append("Vessel type matches cargo")
            elif ('tanker' in vessel_type and 'oil' in cargo_type):
                score += 0.3
                reason.append("Tanker suitable for liquid cargo")
            elif any(t in vessel_type for t in ['cargo', 'general']):
                score += 0.2
                reason.append("General cargo vessel")

            # Size matching (30% of score)
            cargo_quantity = float(cargo.quantity) if cargo.quantity else 0
            vessel_dwt = float(vessel.get('dwt', 0))
            
            if vessel_dwt > 0 and cargo_quantity > 0:
                utilization = cargo_quantity / vessel_dwt
                if 0.5 <= utilization <= 0.95:
                    score += 0.3
                    reason.append(f"Optimal vessel size ({utilization:.0%} utilization)")
                elif 0.3 <= utilization < 0.5:
                    score += 0.2
                    reason.append(f"Acceptable vessel size ({utilization:.0%} utilization)")
                elif utilization < 1.0:
                    score += 0.1
                    reason.append(f"Vessel has sufficient capacity")

            if score >= 0.3:  # Only include vessels with reasonable match score
                matching_vessels.append({
                    "vessel": {
                        "name": vessel.get('name', 'Unknown'),
                        "type": vessel.get('type', 'Unknown'),
                        "position": vessel.get('position', 'Unknown'),
                        "status": vessel.get('status', 'Unknown'),
                        "speed": vessel.get('speed', '0 kn'),
                        "distance_to_load": f"{distance:.0f} nm" if 'distance' in locals() else "Unknown",
                        "mmsi": vessel.get('mmsi', 'Unknown')
                    },
                    "score": score,
                    "reason": "; ".join(reason)
                })

        # Sort by score and return top matches
        matching_vessels.sort(key=lambda x: x['score'], reverse=True)
        return matching_vessels[:10]

    except Exception as e:
        logger.error(f"Error matching vessels: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cargoes/{cargo_id}", response_model=CargoResponse)
async def get_cargo(cargo_id: int, db: Session = Depends(get_db)):
    """Get a specific cargo"""
    cargo = db.query(Cargo).filter(Cargo.id == cargo_id).first()
    if cargo is None:
        raise HTTPException(status_code=404, detail="Cargo not found")
    return cargo