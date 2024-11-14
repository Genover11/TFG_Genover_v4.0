# src/ship_broker/api/routes/email_processing.py
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict
import logging

from ...core.email_parser import EmailParser
from ...core.database import Vessel, Cargo
from ...config import Settings, get_settings
from ..dependencies import get_db

router = APIRouter()

@router.post("/process-emails/")
async def process_emails(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
) -> Dict[str, str]:
    """Process emails and extract vessel/cargo information"""
    try:
        parser = EmailParser(
            settings.EMAIL_ADDRESS,
            settings.EMAIL_PASSWORD,
            settings.IMAP_SERVER
        )
        
        emails = parser.get_emails(days=1)
        print(f"Found {len(emails)} emails to process")
        
        for email_data in emails:
            vessels = parser.extract_vessels(email_data['content'])
            for vessel in vessels:
                db_vessel = Vessel(
                    name=vessel.name,
                    dwt=vessel.dwt,
                    position=vessel.position,
                    vessel_type=vessel.vessel_type,
                    description=vessel.description
                )
                db.add(db_vessel)
            
            cargoes = parser.extract_cargoes(email_data['content'])
            for cargo in cargoes:
                db_cargo = Cargo(
                    cargo_type=cargo.cargo_type,
                    quantity=cargo.quantity,
                    load_port=cargo.load_port,
                    discharge_port=cargo.discharge_port,
                    rate=cargo.rate,
                    description=cargo.description,
                    laycan_start=cargo.laycan_start,
                    laycan_end=cargo.laycan_end
                )
                db.add(db_cargo)
        
        db.commit()
        return {"message": f"Successfully processed {len(emails)} emails"}
        
    except Exception as e:
        print(f"Error processing emails: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process emails: {str(e)}"
        )