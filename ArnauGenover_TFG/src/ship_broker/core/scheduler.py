# src/ship_broker/core/scheduler.py

import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from .database import SessionLocal
from .email_parser import EmailParser
from .auction_background import check_vessels_for_auctions
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

async def process_emails(db: Session):
    """Process new emails"""
    try:
        parser = EmailParser(
            settings.EMAIL_ADDRESS,
            settings.EMAIL_PASSWORD,
            db,
            settings.IMAP_SERVER
        )
        emails = parser.get_emails(days=1)
        for email_data in emails:
            parser.process_and_store_email(email_data)
    except Exception as e:
        logger.error(f"Error processing emails: {str(e)}")

async def start_scheduler():
    """Start background tasks"""
    while True:
        try:
            db = SessionLocal()
            try:
                # Process emails
                await process_emails(db)
                
                # Check for vessels that need auctions
                await check_vessels_for_auctions(db)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in scheduler: {str(e)}")
            
        # Wait before next check
        await asyncio.sleep(settings.EMAIL_CHECK_INTERVAL)  # Usually 300 seconds (5 minutes)