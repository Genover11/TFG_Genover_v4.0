# src/ship_broker/api/routes/email_processing.py
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict
import logging
from datetime import datetime

from ...core.email_parser import EmailParser
from ...core.database import Vessel, Cargo, ProcessedEmail  # Added ProcessedEmail import
from ...config import Settings, get_settings
from ..dependencies import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/process-emails/")
async def process_emails(
    reprocess: bool = False,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
) -> Dict[str, str]:
    """Process emails and extract vessel/cargo information"""
    try:
        parser = EmailParser(
            email_address=settings.EMAIL_ADDRESS,
            password=settings.EMAIL_PASSWORD,
            db=db,
            imap_server=settings.IMAP_SERVER
        )
        
        if reprocess:
            try:
                db.query(ProcessedEmail).delete()
                db.query(Cargo).delete()
                db.query(Vessel).delete()
                db.commit()
            except Exception as e:
                logger.error(f"Error clearing database: {str(e)}")
                db.rollback()
        
        emails = parser.get_emails(days=1)
        logger.info(f"Found {len(emails)} emails to process")
        
        total_vessels = 0
        total_cargoes = 0
        
        for email_data in emails:
            try:
                logger.info(f"Processing email with subject: {email_data['subject']}")
                vessels, cargoes = parser.process_and_store_email(email_data)
                total_vessels += len(vessels)
                total_cargoes += len(cargoes)
            except Exception as e:
                logger.error(f"Error processing individual email: {str(e)}")
                continue
        
        return {
            "status": "success",
            "message": f"Processed {len(emails)} emails. Found {total_vessels} vessels and {total_cargoes} cargoes",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in email processing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )