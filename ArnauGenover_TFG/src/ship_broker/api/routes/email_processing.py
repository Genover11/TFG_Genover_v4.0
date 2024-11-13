# src/ship_broker/api/routes/email_processing.py
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from typing import Dict

from ...core.email_parser import EmailParser
from ...core.database import Vessel, Cargo
from ...config import Settings, get_settings
from ..dependencies import get_db

router = APIRouter()

def process_emails(settings: Settings, db: Session):
    """
    Process emails to extract vessel and cargo information and save them to the database.
    """
    parser = EmailParser(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD, settings.IMAP_SERVER)
    emails = parser.get_emails(days=7)
    
    for email_data in emails:
        vessels = parser.extract_vessels(email_data['content'])
        cargoes = parser.extract_cargoes(email_data['content'])
        
        # Save to database
        for vessel in vessels:
            db_vessel = Vessel(**vessel.__dict__)
            db.add(db_vessel)
        
        for cargo in cargoes:
            db_cargo = Cargo(**cargo.__dict__)
            db.add(db_cargo)
        
        db.commit()

@router.post("/process-emails/", response_model=Dict[str, str])
async def start_email_processing(
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db)
):
    """
    Start email processing in the background to extract and store vessel and cargo information.
    """
    background_tasks.add_task(process_emails, settings, db)
    return {"message": "Email processing started"}