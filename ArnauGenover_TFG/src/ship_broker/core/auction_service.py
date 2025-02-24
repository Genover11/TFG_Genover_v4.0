# src/ship_broker/core/auction_service.py

from datetime import datetime, timedelta
from typing import Optional, List
import logging
from sqlalchemy.orm import Session
from .database import Vessel, Auction, AuctionStatus

logger = logging.getLogger(__name__)

class AuctionService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_active_auctions(self) -> List[Auction]:
        """Get all active auctions"""
        try:
            return self.db.query(Auction).filter(
                Auction.status == AuctionStatus.ACTIVE,
                Auction.end_date > datetime.utcnow()
            ).all()
        except Exception as e:
            logger.error(f"Error getting active auctions: {str(e)}")
            return []
    
    def calculate_auction_parameters(self, vessel: Vessel) -> dict:
        """Calculate auction parameters based on vessel characteristics"""
        # Base parameters
        base_price = 20.0  # Base price per MT
        duration_days = 15  # Standard auction duration

        # Adjust prices based on vessel size
        if vessel.dwt > 100000:  # Large vessels
            start_price = base_price * 1.2
            min_price = base_price * 0.6
        elif vessel.dwt > 50000:  # Medium vessels
            start_price = base_price * 1.1
            min_price = base_price * 0.55
        else:  # Small vessels
            start_price = base_price
            min_price = base_price * 0.5

        # Calculate daily reduction
        daily_reduction = (start_price - min_price) / duration_days

        return {
            "start_price": start_price,
            "min_price": min_price,
            "daily_reduction": daily_reduction,
            "duration_days": duration_days
        }
    
    def create_auction_for_vessel(self, vessel_id: int) -> Optional[Auction]:
        """Create a new auction for a vessel"""
        try:
            # Get and validate vessel
            vessel = self.db.query(Vessel).filter(Vessel.id == vessel_id).first()
            if not vessel:
                logger.error(f"No vessel found with ID {vessel_id}")
                return None

            if not vessel.dwt:
                logger.error(f"Vessel {vessel_id} has no DWT specified")
                return None

            # Check for existing active auction
            existing_auction = self.db.query(Auction).filter(
                Auction.vessel_id == vessel_id,
                Auction.status == AuctionStatus.ACTIVE
            ).first()

            if existing_auction:
                logger.info(f"Vessel {vessel_id} already has an active auction")
                return existing_auction

            # Calculate auction parameters
            params = self.calculate_auction_parameters(vessel)
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=params["duration_days"])

            # Create auction
            auction = Auction(
                vessel_id=vessel.id,
                start_date=start_date,
                end_date=end_date,
                space_mt=vessel.dwt,
                space_sold_mt=0.0,
                start_price=params["start_price"],
                current_price=params["start_price"],
                min_price=params["min_price"],
                daily_reduction=params["daily_reduction"],
                status=AuctionStatus.ACTIVE,
                last_updated=start_date
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
            active_auctions = self.get_active_auctions()
            if not active_auctions:
                return

            updated_count = 0
            now = datetime.utcnow()

            for auction in active_auctions:
                try:
                    # Calculate time elapsed
                    hours_elapsed = (now - auction.start_date).total_seconds() / 3600
                    
                    # Calculate new price with hourly granularity
                    hourly_reduction = auction.daily_reduction / 24
                    price_reduction = hourly_reduction * hours_elapsed
                    
                    # Update price if significant change
                    new_price = round(max(
                        auction.start_price - price_reduction,
                        auction.min_price
                    ), 2)
                    
                    if abs(new_price - auction.current_price) >= 0.01:
                        auction.current_price = new_price
                        auction.last_updated = now
                        updated_count += 1
                    
                    # Check auction completion conditions
                    if now > auction.end_date:
                        auction.status = AuctionStatus.COMPLETED
                        logger.info(f"Completed auction {auction.id} due to end date reached")
                    elif auction.space_sold_mt and auction.space_sold_mt >= auction.space_mt * 0.999:
                        auction.status = AuctionStatus.COMPLETED
                        logger.info(f"Completed auction {auction.id} due to all space sold")
                        
                except Exception as e:
                    logger.error(f"Error updating auction {auction.id}: {str(e)}")
                    continue

            if updated_count > 0:
                self.db.commit()
                logger.info(f"Updated prices for {updated_count} active auctions")

        except Exception as e:
            logger.error(f"Error in update_auction_prices: {str(e)}")
            self.db.rollback()

    def get_auction_statistics(self, auction_id: int) -> dict:
        """Get statistics for an auction"""
        try:
            auction = self.db.query(Auction).filter(Auction.id == auction_id).first()
            if not auction:
                return {}

            space_sold = auction.space_sold_mt or 0
            space_remaining = auction.space_mt - space_sold

            return {
                "total_space": auction.space_mt,
                "space_sold": space_sold,
                "space_remaining": space_remaining,
                "space_utilization": (space_sold / auction.space_mt * 100) if auction.space_mt > 0 else 0,
                "price_drop": ((auction.start_price - auction.current_price) / auction.start_price * 100) 
                             if auction.start_price > 0 else 0,
                "days_remaining": (auction.end_date - datetime.utcnow()).days if auction.end_date else 0,
                "status": auction.status.value,
                "vessel_name": auction.vessel.name if auction.vessel else "Unknown",
                "vessel_type": auction.vessel.vessel_type if auction.vessel else "Unknown",
                "start_date": auction.start_date.isoformat() if auction.start_date else None,
                "end_date": auction.end_date.isoformat() if auction.end_date else None,
                "last_updated": auction.last_updated.isoformat() if auction.last_updated else None
            }
            
        except Exception as e:
            logger.error(f"Error getting auction statistics for auction {auction_id}: {str(e)}")
            return {}