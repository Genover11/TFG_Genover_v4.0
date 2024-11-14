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