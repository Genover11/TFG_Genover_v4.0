# src/ship_broker/api/routes/auctions.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
import logging
from datetime import datetime, timedelta
import random

from ...core.database import Auction, AuctionStatus, Vessel
from ...core.auction_service import AuctionService
from ..dependencies import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/debug/create-test-auction", tags=["debug"])
async def create_test_auction(db: Session = Depends(get_db)):
    """Create a test auction with sample data"""
    logger.info("Starting test auction creation...")
    try:
        # Create a new test vessel with random data
        vessel_types = ["BULK CARRIER", "SUPRAMAX", "PANAMAX", "HANDYSIZE"]
        ports = ["SINGAPORE", "ROTTERDAM", "SANTOS", "QINGDAO", "HOUSTON"]
        
        vessel = Vessel(
            name=f"TEST VESSEL {random.randint(1000, 9999)}",
            dwt=random.randint(30000, 90000),
            position=random.choice(ports),
            eta=datetime.utcnow() + timedelta(days=random.randint(1, 7)),
            vessel_type=random.choice(vessel_types),
            description="Test vessel for auction"
        )
        
        db.add(vessel)
        db.commit()
        db.refresh(vessel)
        logger.info(f"Created test vessel with ID {vessel.id}")

        # Create auction for vessel
        logger.info(f"Creating auction for vessel {vessel.id}...")
        service = AuctionService(db)
        auction = service.create_auction_for_vessel(vessel.id)
        
        if auction:
            logger.info(f"Successfully created auction {auction.id}")
            return {
                "success": True,
                "message": "Test auction created",
                "auction_id": auction.id,
                "vessel_id": vessel.id,
                "details": {
                    "vessel_name": vessel.name,
                    "start_price": auction.start_price,
                    "end_date": auction.end_date.isoformat() if auction.end_date else None
                }
            }
        logger.error("Failed to create auction")
        return {"success": False, "message": "Failed to create auction"}
    except Exception as e:
        logger.error(f"Error creating test auction: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/auctions/active")
async def get_active_auctions(db: Session = Depends(get_db)):
    """Get all active auctions"""
    logger.info("Getting active auctions...")
    try:
        service = AuctionService(db)
        service.update_auction_prices()
        
        auctions = db.query(Auction).filter(
            Auction.status == AuctionStatus.ACTIVE
        ).all()
        
        logger.info(f"Found {len(auctions)} active auctions")
        return [{
            "id": auction.id,
            "vessel_id": auction.vessel_id,
            "vessel_name": auction.vessel.name if auction.vessel else "Unknown",
            "vessel_type": auction.vessel.vessel_type if auction.vessel else "Unknown",
            "space_mt": auction.space_mt,
            "start_price": auction.start_price,
            "current_price": auction.current_price,
            "min_price": auction.min_price,
            "days_remaining": (auction.end_date - datetime.utcnow()).days if auction.end_date else 0,
            "end_date": auction.end_date.isoformat() if auction.end_date else None
        } for auction in auctions]
    except Exception as e:
        logger.error(f"Error getting active auctions: {str(e)}")
        return []

@router.get("/auctions/past")
async def get_past_auctions(db: Session = Depends(get_db)):
    """Get completed auctions"""
    logger.info("Getting past auctions...")
    try:
        auctions = db.query(Auction).filter(
            Auction.status == AuctionStatus.COMPLETED
        ).order_by(Auction.end_date.desc()).limit(10).all()
        
        logger.info(f"Found {len(auctions)} past auctions")
        return [{
            "id": auction.id,
            "vessel_name": auction.vessel.name if auction.vessel else "Unknown",
            "space_mt": auction.space_mt,
            "start_price": auction.start_price,
            "final_price": auction.current_price,
            "end_date": auction.end_date.isoformat() if auction.end_date else None,
            "status": auction.status.value
        } for auction in auctions]
    except Exception as e:
        logger.error(f"Error getting past auctions: {str(e)}")
        return []

@router.post("/auctions/{auction_id}/accept")
async def accept_auction_price(auction_id: int, db: Session = Depends(get_db)):
    """Accept current auction price"""
    try:
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(status_code=404, detail="Auction not found")
            
        if auction.status != AuctionStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Auction is not active")
            
        # Complete the auction
        auction.status = AuctionStatus.COMPLETED
        db.commit()
        
        return {"success": True, "message": "Price accepted successfully"}
    except Exception as e:
        logger.error(f"Error accepting auction price: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))