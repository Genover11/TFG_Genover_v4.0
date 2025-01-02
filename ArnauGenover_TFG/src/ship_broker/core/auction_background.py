# src/ship_broker/core/auction_background.py

from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from .database import Vessel, Auction, AuctionStatus
from .auction_service import AuctionService

logger = logging.getLogger(__name__)

async def check_vessels_for_auctions(db: Session):
    """
    Check all vessels with ETAs and create auctions if needed.
    Should be run periodically to catch any vessels that might have been missed.
    """
    try:
        # Get all vessels with ETAs that don't have active auctions
        vessels = db.query(Vessel).filter(
            Vessel.eta.isnot(None)  # Has ETA
        ).all()
        
        auction_service = AuctionService(db)
        created_count = 0
        
        for vessel in vessels:
            # Check if vessel already has an active auction
            existing_auction = db.query(Auction).filter(
                Auction.vessel_id == vessel.id,
                Auction.status == AuctionStatus.ACTIVE
            ).first()
            
            if not existing_auction and vessel.eta > datetime.utcnow():
                # Create new auction
                auction = auction_service.create_auction_for_vessel(vessel.id)
                if auction:
                    created_count += 1
                    logger.info(f"Created auction for vessel {vessel.name} (ID: {vessel.id})")
        
        if created_count > 0:
            logger.info(f"Created {created_count} new auctions from existing vessels")
            
    except Exception as e:
        logger.error(f"Error checking vessels for auctions: {str(e)}")
        db.rollback()