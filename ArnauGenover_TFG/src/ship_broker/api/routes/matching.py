# src/ship_broker/api/routes/matching.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict

from ...core.matcher import CargoMatcher
from ...core.vessel_tracker import VesselTracker
from ...config import get_settings
from ..dependencies import get_db

router = APIRouter()

@router.get("/match/cargo/{cargo_id}/vessels")
async def find_vessels_for_cargo(
    cargo_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
) -> List[Dict]:
    tracker = VesselTracker(api_key=settings.ZENSCRAPE_API_KEY)
    matcher = CargoMatcher(db, tracker)
    matches = matcher.find_vessels_for_cargo(cargo_id)
    return matches