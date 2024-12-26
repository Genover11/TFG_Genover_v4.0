# src/ship_broker/api/routes/matching.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
import logging

from ...core.vessel_tracker import VesselTracker
from ...core.cargo_tracker import CargoTracker
from ...core.database import Vessel, Cargo
from ...config import Settings, get_settings
from ..dependencies import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/match/cargo/{cargo_id}/vessels", response_model=List[Dict])
async def find_vessels_for_cargo(
    cargo_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    """Find available vessels for a specific cargo"""
    try:
        # Get cargo details
        cargo = db.query(Cargo).filter(Cargo.id == cargo_id).first()
        if not cargo:
            raise HTTPException(status_code=404, detail="Cargo not found")

        # Initialize vessel tracker
        tracker = VesselTracker(api_key=settings.ZENSCRAPE_API_KEY)
        
        # Get vessels in loading port
        vessels = tracker.get_vessels_in_port(cargo.load_port or "UNKNOWN PORT")
        
        # Calculate match scores
        matches = []
        for vessel in vessels:
            if _is_vessel_suitable(vessel, cargo):
                score = _calculate_match_score(vessel, cargo)
                matches.append({
                    "vessel": vessel,
                    "score": score,
                    "reason": _get_match_reason(vessel, cargo)
                })
        
        return sorted(matches, key=lambda x: x['score'], reverse=True)

    except Exception as e:
        logger.error(f"Error finding vessels: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/match/vessel/{vessel_id}/cargoes", response_model=List[Dict])
async def find_cargoes_for_vessel(
    vessel_id: int,
    db: Session = Depends(get_db)
):
    """Find available cargoes for a specific vessel"""
    try:
        # Get vessel details
        vessel = db.query(Vessel).filter(Vessel.id == vessel_id).first()
        if not vessel:
            raise HTTPException(status_code=404, detail="Vessel not found")

        # Create cargo tracker
        tracker = CargoTracker()
        
        # Get matching cargoes
        vessel_data = {
            'position': vessel.position,
            'type': vessel.vessel_type,
            'dwt': vessel.dwt
        }
        
        cargoes = tracker.get_cargoes_for_vessel(vessel_data)
        return cargoes

    except Exception as e:
        logger.error(f"Error finding cargoes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def _is_vessel_suitable(vessel: Dict, cargo: Cargo) -> bool:
    """Check if vessel is suitable for cargo"""
    if not vessel.get('dwt') or not cargo.quantity:
        return False
    
    # Check if vessel size is appropriate for cargo
    return (vessel['dwt'] * 0.95) >= cargo.quantity >= (vessel['dwt'] * 0.3)

def _calculate_match_score(vessel: Dict, cargo: Cargo) -> float:
    """Calculate match score between vessel and cargo"""
    score = 0.0
    
    # Size compatibility (40% of score)
    if cargo.quantity and vessel.get('dwt'):
        utilization = cargo.quantity / vessel['dwt']
        score += min(1.0, utilization) * 0.4

    # Location score (30% of score)
    if vessel.get('position') and cargo.load_port:
        score += 0.3

    # Timing score (30% of score)
    if vessel.get('eta') and cargo.laycan_start:
        score += 0.3

    return min(1.0, score)

def _get_match_reason(vessel: Dict, cargo: Cargo) -> str:
    """Get human-readable reason for match"""
    reasons = []
    
    if vessel.get('dwt') and cargo.quantity:
        utilization = (cargo.quantity / vessel['dwt']) * 100
        reasons.append(f"Vessel capacity utilization: {utilization:.1f}%")
    
    if vessel.get('position'):
        reasons.append(f"Currently in/near {vessel['position']}")
        
    if vessel.get('eta') and cargo.laycan_start:
        reasons.append(f"Timing compatible")
        
    return "; ".join(reasons) if reasons else "No specific matching criteria"