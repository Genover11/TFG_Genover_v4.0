# src/ship_broker/core/auction_service.py

from datetime import datetime, timedelta
from typing import Optional
import logging
from sqlalchemy.orm import Session
from .database import Vessel, Auction, AuctionStatus

logger = logging.getLogger(__name__)

class AuctionService:
    def __init__(self, db: Session):
        self.db = db

    def create_auction_for_vessel(self, vessel_id: int) -> Optional[Auction]:
        """Create an auction for a vessel if it has an ETA"""
        try:
            vessel = self.db.query(Vessel).filter(Vessel.id == vessel_id).first()
            if not vessel:
                logger.error(f"No vessel found with ID {vessel_id}")
                return None

            # Check if vessel already has an active auction
            existing_auction = self.db.query(Auction).filter(
                Auction.vessel_id == vessel_id,
                Auction.status == AuctionStatus.ACTIVE
            ).first()

            if existing_auction:
                logger.info(f"Vessel {vessel_id} already has an active auction")
                return existing_auction

            # Calculate auction parameters
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=15)  # 15-day auction period
            
            # Calculate prices
            if vessel.dwt:
                start_price = 20.0  # USD per MT
                min_price = 10.0    # USD per MT
                daily_reduction = (start_price - min_price) / 15  # Even reduction over 15 days
            else:
                logger.error(f"Vessel {vessel_id} has no DWT specified")
                return None

            # Create auction
            auction = Auction(
                vessel_id=vessel.id,
                start_date=start_date,
                end_date=end_date,
                space_mt=vessel.dwt,  # Use vessel's DWT as available space
                start_price=start_price,
                current_price=start_price,  # Initially same as start price
                min_price=min_price,
                daily_reduction=daily_reduction,
                status=AuctionStatus.ACTIVE
            )

            self.db.add(auction)
            self.db.commit()
            self.db.refresh(auction)

            logger.info(f"Created auction for vessel {vessel.name} (ID: {vessel.id})")
            return auction

        except Exception as e:
            logger.error(f"Error creating auction for vessel {vessel_id}: {str(e)}")
            self.db.rollback()
            return None

    def update_auction_prices(self):
        """Update current prices for all active auctions"""
        try:
            active_auctions = self.db.query(Auction).filter(
                Auction.status == AuctionStatus.ACTIVE
            ).all()

            updated_count = 0
            for auction in active_auctions:
                days_elapsed = (datetime.utcnow() - auction.start_date).days
                
                # Calculate new price
                price_reduction = auction.daily_reduction * days_elapsed
                new_price = max(auction.start_price - price_reduction, auction.min_price)
                
                # Update price
                auction.current_price = new_price
                updated_count += 1
                
                # Close auction if end date reached
                if datetime.utcnow() > auction.end_date:
                    auction.status = AuctionStatus.COMPLETED
                    logger.info(f"Completed auction {auction.id} for vessel {auction.vessel_id}")

            if updated_count > 0:
                self.db.commit()

            logger.info(f"Updated prices for {updated_count} active auctions")

        except Exception as e:
            logger.error(f"Error updating auction prices: {str(e)}")
            self.db.rollback()