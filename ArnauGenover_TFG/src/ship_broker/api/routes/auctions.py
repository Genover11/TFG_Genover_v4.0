# src/ship_broker/api/routes/auctions.py

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Dict
import logging
from datetime import datetime, timedelta
import random
from pydantic import BaseModel, Field

from ...core.database import Auction, AuctionStatus, Vessel, AuctionBid
from ...core.auction_service import AuctionService
from ..dependencies import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

class AcceptBidRequest(BaseModel):
    space_percentage: float = Field(default=100.0, ge=0.0, le=100.0)

@router.get("/auctions/debug/create-test-auction", tags=["debug"])
async def create_test_auction(db: Session = Depends(get_db)):
    """Create a test auction with sample data"""
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
    try:
        service = AuctionService(db)
        service.update_auction_prices()
        
        auctions = service.get_active_auctions()
        logger.info(f"Found {len(auctions)} active auctions")
        
        return [{
            "id": auction.id,
            "vessel_id": auction.vessel_id,
            "vessel_name": auction.vessel.name if auction.vessel else "Unknown",
            "vessel_type": auction.vessel.vessel_type if auction.vessel else "Unknown",
            "space_mt": auction.space_mt,
            "space_sold_mt": auction.space_sold_mt or 0,
            "available_space_mt": auction.space_mt - (auction.space_sold_mt or 0),
            "start_price": auction.start_price,
            "current_price": auction.current_price,
            "min_price": auction.min_price,
            "days_remaining": (auction.end_date - datetime.utcnow()).days if auction.end_date else 0,
            "end_date": auction.end_date.isoformat() if auction.end_date else None
        } for auction in auctions if auction.space_mt > (auction.space_sold_mt or 0)]
    except Exception as e:
        logger.error(f"Error getting active auctions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/auctions/past")
async def get_past_auctions(db: Session = Depends(get_db)):
    """Get all auction bids history"""
    try:
        # Get all bids ordered by most recent first
        bids = db.query(AuctionBid).\
            join(Auction).\
            join(Vessel).\
            order_by(AuctionBid.sold_at.desc()).\
            limit(50).all()
        
        return [{
            "id": bid.id,
            "vessel_name": bid.auction.vessel.name if bid.auction.vessel else "Unknown",
            "space_mt": bid.auction.space_mt,
            "bid_space_mt": bid.bid_space_mt,
            "remaining_space_mt": bid.auction.space_mt - bid.auction.space_sold_mt if bid.auction else 0,
            "percentage_sold": (bid.bid_space_mt / bid.auction.space_mt * 100) if bid.auction else 0,
            "sale_price": bid.sale_price,
            "sold_at": bid.sold_at.isoformat() if bid.sold_at else None,
            "status": "FINAL BID" if bid.auction and (bid.auction.space_mt - bid.auction.space_sold_mt <= 0) else "PARTIAL BID"
        } for bid in bids]
    except Exception as e:
        logger.error(f"Error getting auction bids: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auctions/{auction_id}/accept")
async def accept_auction_price(
    auction_id: int, 
    bid: AcceptBidRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Accept current auction price for a percentage of total space"""
    try:
        # Get auction and verify it exists
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(status_code=404, detail="Auction not found")
            
        # Verify auction is active
        if auction.status != AuctionStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Auction is not active")
            
        # Verify auction hasn't expired
        if datetime.utcnow() > auction.end_date:
            raise HTTPException(status_code=400, detail="Auction has expired")

        # Calculate space and validate
        space_to_purchase = (auction.space_mt * bid.space_percentage / 100)
        available_space = auction.space_mt - (auction.space_sold_mt or 0)
        
        if space_to_purchase > available_space:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot purchase {bid.space_percentage}%. Only {((available_space / auction.space_mt) * 100):.1f}% remaining"
            )
            
        # Create new bid record
        new_bid = AuctionBid(
            auction_id=auction.id,
            bid_space_mt=space_to_purchase,
            sale_price=auction.current_price,
            sold_at=datetime.utcnow()
        )
        db.add(new_bid)
            
        # Update auction
        auction.space_sold_mt = (auction.space_sold_mt or 0) + space_to_purchase
        auction.last_updated = datetime.utcnow()
        
        # Check if auction should be completed
        if auction.space_sold_mt >= auction.space_mt * 0.999:  # 99.9% sold
            auction.status = AuctionStatus.COMPLETED
            logger.info(f"Auction {auction_id} completed - all space sold")
        else:
            logger.info(f"Auction {auction_id} partial sale: {space_to_purchase:.2f} MT ({bid.space_percentage}%)")
        
        db.commit()
        
        return {
            "success": True, 
            "message": f"Successfully purchased {space_to_purchase:.2f} MT ({bid.space_percentage}%) of space",
            "current_price": auction.current_price,
            "remaining_space": auction.space_mt - auction.space_sold_mt
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error accepting auction price: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))