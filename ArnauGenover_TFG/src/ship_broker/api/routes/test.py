# src/ship_broker/api/routes/test.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List
from datetime import datetime

from ...core.database import Vessel, Cargo
from ...core.email_parser import EmailParser
from ...config import Settings, get_settings
from ..dependencies import get_db

router = APIRouter()  # Define router first

@router.post("/test/create-sample-data/")
async def create_sample_data(db: Session = Depends(get_db)):
    """Create sample vessels and cargoes for testing"""
    # Sample vessels
    sample_vessels = [
        Vessel(
            name="STAR BULK",
            dwt=82000.0,
            position="SINGAPORE",
            eta=datetime.now(),
            vessel_type="BULK CARRIER",
            description="Modern bulk carrier available for charter"
        ),
        Vessel(
            name="PACIFIC TRADER",
            dwt=55000.0,
            position="ROTTERDAM",
            vessel_type="SUPRAMAX",
            description="Supramax vessel open for orders"
        )
    ]
    
    for vessel in sample_vessels:
        db.add(vessel)
    
    # Sample cargoes
    sample_cargoes = [
        Cargo(
            cargo_type="GRAIN",
            quantity=50000.0,
            load_port="SANTOS",
            discharge_port="QINGDAO",
            rate="$25.50",
            description="Soybean cargo for prompt delivery",
            laycan_start=datetime.now(),
            laycan_end=datetime.now()
        )
    ]
    
    for cargo in sample_cargoes:
        db.add(cargo)
    
    db.commit()
    return {"message": "Sample data created successfully"}

@router.get("/test/debug-last-email/")
async def debug_last_email(
    settings: Settings = Depends(get_settings)
) -> Dict[str, str]:
    """Debug the last email received"""
    try:
        parser = EmailParser(
            settings.EMAIL_ADDRESS,
            settings.EMAIL_PASSWORD,
            settings.IMAP_SERVER
        )
        emails = parser.get_emails(days=1)
        
        if not emails:
            return {"message": "No emails found in the last 24 hours"}
            
        last_email = emails[-1]
        return {
            "subject": last_email['subject'],
            "content": last_email['content']
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Debug error: {str(e)}"
        )


@router.get("/test/db-contents/")
async def view_db_contents(db: Session = Depends(get_db)):
    """View all database contents"""
    vessels = db.query(Vessel).all()
    cargoes = db.query(Cargo).all()
    
    return {
        "vessels": [
            {
                "name": v.name,
                "type": v.vessel_type,
                "position": v.position,
                "dwt": v.dwt,
                "created_at": v.created_at
            } for v in vessels
        ],
        "cargoes": [
            {
                "type": c.cargo_type,
                "quantity": c.quantity,
                "load_port": c.load_port,
                "discharge_port": c.discharge_port,
                "created_at": c.created_at
            } for c in cargoes
        ]
    }

@router.get("/test/clear-database/")
async def clear_database(db: Session = Depends(get_db)):
    """Clear all data from database"""
    db.query(Vessel).delete()
    db.query(Cargo).delete()
    db.commit()
    return {"message": "Database cleared successfully"}