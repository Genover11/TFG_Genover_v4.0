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

@router.get("", response_model=List[CargoResponse])
@router.get("/", response_model=List[CargoResponse])  # Adding both paths to handle both cases
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

# Add the matching endpoint here too since it's cargo-related
@router.get("/match/{cargo_id}/vessels", response_model=List[Dict])
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

            # Location matching
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

            # Type matching
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

            if score >= 0.3:  # Only include vessels with reasonable match score
                matching_vessels.append({
                    "vessel": vessel,
                    "score": score,
                    "reason": "; ".join(reason)
                })

        # Sort by score and return top matches
        matching_vessels.sort(key=lambda x: x['score'], reverse=True)
        return matching_vessels[:10]

    except Exception as e:
        logger.error(f"Error matching vessels: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Rest of your cargo routes...