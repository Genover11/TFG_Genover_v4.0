# src/ship_broker/core/scheduler.py
import asyncio
from datetime import datetime
from ..core.database import SessionLocal, Vessel, Cargo
from ..core.email_parser import EmailParser
from ..config import settings

async def process_emails():
    """Process emails and save data to database"""
    db = SessionLocal()
    try:
        parser = EmailParser(
            email_address=settings.EMAIL_ADDRESS,
            password=settings.EMAIL_PASSWORD,
            db=db,  # Pass the database session
            imap_server=settings.IMAP_SERVER
        )
        
        emails = parser.get_emails(days=1)  # Get last 24 hours emails
        
        for email_data in emails:
            try:
                vessels, cargoes = parser.process_and_store_email(email_data)
                print(f"Processed email at {datetime.now()}: Found {len(vessels)} vessels and {len(cargoes)} cargoes")
            except Exception as e:
                print(f"Error processing individual email: {str(e)}")
                continue
                
    except Exception as e:
        print(f"Error processing emails: {str(e)}")
        db.rollback()
    finally:
        db.close()

async def start_scheduler():
    """Start the background task to process emails periodically"""
    while True:
        try:
            await process_emails()
        except Exception as e:
            print(f"Scheduler error: {str(e)}")
        await asyncio.sleep(300)  # Wait 5 minutes