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
            settings.EMAIL_ADDRESS,
            settings.EMAIL_PASSWORD,
            settings.IMAP_SERVER
        )
        emails = parser.get_emails(days=1)  # Get last 24 hours emails
        
        for email_data in emails:
            vessels = parser.extract_vessels(email_data['content'])
            cargoes = parser.extract_cargoes(email_data['content'])
            
            # Save to database with duplicate checking
            for vessel in vessels:
                existing = db.query(Vessel).filter_by(
                    name=vessel.name,
                    dwt=vessel.dwt
                ).first()
                if not existing:
                    db_vessel = Vessel(**vessel.__dict__)
                    db.add(db_vessel)
            
            for cargo in cargoes:
                existing = db.query(Cargo).filter_by(
                    cargo_type=cargo.cargo_type,
                    quantity=cargo.quantity,
                    load_port=cargo.load_port,
                    discharge_port=cargo.discharge_port
                ).first()
                if not existing:
                    db_cargo = Cargo(**cargo.__dict__)
                    db.add(db_cargo)
            
            db.commit()
            print(f"Processed email at {datetime.now()}: Found {len(vessels)} vessels and {len(cargoes)} cargoes")
    except Exception as e:
        print(f"Error processing emails: {e}")
    finally:
        db.close()

async def start_scheduler():
    """Start the background task to process emails periodically"""
    while True:
        await process_emails()
        await asyncio.sleep(300)  # Wait 5 minutes