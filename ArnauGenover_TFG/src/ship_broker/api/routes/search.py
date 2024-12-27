# src/ship_broker/api/routes/search.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime
import logging

from ...core.database import Vessel, Cargo
from ...core.schemas import VesselSearch, CargoSearch, Vessel as VesselSchema, Cargo as CargoSchema
from ...core.vessel_tracker import VesselTracker
from ...core.cargo_tracker import CargoTracker
from ..dependencies import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/search/vessels/", response_model=List[VesselSchema])
async def search_vessels(
    params: VesselSearch = Depends(),
    include_live: bool = False,
    db: Session = Depends(get_db)
):
    """Search vessels with filters and optional live data from VesselFinder"""
    try:
        # Query database
        query = db.query(Vessel)
        
        if params.name:
            query = query.filter(Vessel.name.ilike(f"%{params.name}%"))
        if params.vessel_type:
            query = query.filter(Vessel.vessel_type.ilike(f"%{params.vessel_type}%"))
        if params.position:
            query = query.filter(Vessel.position.ilike(f"%{params.position}%"))
        if params.min_dwt:
            query = query.filter(Vessel.dwt >= params.min_dwt)
        if params.max_dwt:
            query = query.filter(Vessel.dwt <= params.max_dwt)
            
        db_results = query.all()
        
        # Include live data if requested and position is provided
        if include_live and params.position:
            try:
                tracker = VesselTracker()
                live_vessels = tracker.get_vessels_in_port(params.position)
                
                # Convert live data to VesselSchema format and merge with unique results
                for live_vessel in live_vessels:
                    if not any(db_vessel.name == live_vessel['name'] for db_vessel in db_results):
                        db_results.append(Vessel(
                            name=live_vessel['name'],
                            vessel_type=live_vessel['type'],
                            dwt=live_vessel.get('dwt'),
                            position=live_vessel.get('position'),
                            eta=live_vessel.get('eta'),
                            description=live_vessel.get('description', '')
                        ))
            except Exception as e:
                logger.error(f"Error fetching live vessel data: {str(e)}")
        
        return db_results

    except Exception as e:
        logger.error(f"Error searching vessels: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/cargoes/", response_model=List[CargoSchema])
async def search_cargoes(
    params: CargoSearch = Depends(),
    include_live: bool = False,
    db: Session = Depends(get_db)
):
    """Search cargoes with filters and optional live data from ShipNext"""
    try:
        # Query database
        query = db.query(Cargo)
        
        if params.cargo_type:
            query = query.filter(Cargo.cargo_type.ilike(f"%{params.cargo_type}%"))
        if params.load_port:
            query = query.filter(Cargo.load_port.ilike(f"%{params.load_port}%"))
        if params.discharge_port:
            query = query.filter(Cargo.discharge_port.ilike(f"%{params.discharge_port}%"))
        if params.min_quantity:
            query = query.filter(Cargo.quantity >= params.min_quantity)
        if params.max_quantity:
            query = query.filter(Cargo.quantity <= params.max_quantity)
            
        db_results = query.all()
        
        # Include live data if requested
        if include_live:
            try:
                tracker = CargoTracker()
                vessel_data = {
                    'position': params.load_port,
                    'dwt': params.max_quantity or 100000  # Default max value
                }
                live_cargoes = tracker.get_cargoes_for_vessel(vessel_data)
                
                # Merge unique live cargoes with database results
                for live_cargo in live_cargoes:
                    if not any(self._is_duplicate_cargo(db_cargo, live_cargo) 
                             for db_cargo in db_results):
                        db_results.append(Cargo(
                            cargo_type=live_cargo['cargo_type'],
                            quantity=live_cargo['quantity'],
                            load_port=live_cargo['load_port'],
                            discharge_port=live_cargo['discharge_port'],
                            laycan_start=live_cargo.get('laycan_start'),
                            laycan_end=live_cargo.get('laycan_end'),
                            description=live_cargo.get('details', '')
                        ))
            except Exception as e:
                logger.error(f"Error fetching live cargo data: {str(e)}")
        
        return db_results

    except Exception as e:
        logger.error(f"Error searching cargoes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/combined/", response_model=Dict)
async def combined_search(
    position: str,
    min_dwt: Optional[float] = None,
    max_dwt: Optional[float] = None,
    include_live: bool = True,
    db: Session = Depends(get_db)
):
    """Combined search for vessels and matching cargoes in a specific location"""
    try:
        # Search for vessels
        vessel_params = VesselSearch(
            position=position,
            min_dwt=min_dwt,
            max_dwt=max_dwt
        )
        vessels = await search_vessels(
            params=vessel_params,
            include_live=include_live,
            db=db
        )
        
        # Search for cargoes
        cargo_params = CargoSearch(
            load_port=position,
            min_quantity=min_dwt,
            max_quantity=max_dwt
        )
        cargoes = await search_cargoes(
            params=cargo_params,
            include_live=include_live,
            db=db
        )
        
        return {
            "vessels": vessels,
            "cargoes": cargoes,
            "timestamp": datetime.now().isoformat(),
            "search_criteria": {
                "position": position,
                "dwt_range": f"{min_dwt or 'any'} - {max_dwt or 'any'}"
            }
        }
        
    except Exception as e:
        logger.error(f"Error performing combined search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def _is_duplicate_cargo(cargo1: Cargo, cargo2: Dict) -> bool:
    """Check if two cargoes are duplicates based on key attributes"""
    try:
        return (
            cargo1.cargo_type == cargo2['cargo_type'] and
            cargo1.quantity == cargo2['quantity'] and
            cargo1.load_port == cargo2['load_port'] and
            cargo1.discharge_port == cargo2['discharge_port']
        )
    except Exception:
        return False