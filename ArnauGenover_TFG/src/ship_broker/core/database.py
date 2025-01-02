# src/ship_broker/core/database.py

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum
from ..config import settings

engine = create_engine(settings.SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class AuctionStatus(enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ProcessedEmail(Base):
    __tablename__ = "processed_emails"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, unique=True, index=True)
    subject = Column(String)
    processed_at = Column(DateTime, default=datetime.utcnow)


class Vessel(Base):
    __tablename__ = "vessels"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    dwt = Column(Float, nullable=True)
    position = Column(String, nullable=True)
    eta = Column(DateTime, nullable=True)
    open_date = Column(DateTime, nullable=True)
    vessel_type = Column(String, nullable=True)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)  # Make sure this line exists
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add relationship to auctions
    auctions = relationship("Auction", back_populates="vessel", cascade="all, delete-orphan")

class Cargo(Base):
    __tablename__ = "cargoes"
    
    id = Column(Integer, primary_key=True, index=True)
    cargo_type = Column(String)
    quantity = Column(Float, nullable=True)
    load_port = Column(String, nullable=True)
    discharge_port = Column(String, nullable=True)
    laycan_start = Column(DateTime, nullable=True)
    laycan_end = Column(DateTime, nullable=True)
    rate = Column(String, nullable=True)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuctionBid(Base):
    __tablename__ = "auction_bids"
    
    id = Column(Integer, primary_key=True, index=True)
    auction_id = Column(Integer, ForeignKey("auctions.id"))
    bid_space_mt = Column(Float)  # Space purchased in this bid
    sale_price = Column(Float)    # Price at which space was sold
    sold_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    auction = relationship("Auction", back_populates="bids")

class Auction(Base):
    __tablename__ = "auctions"
    
    id = Column(Integer, primary_key=True, index=True)
    vessel_id = Column(Integer, ForeignKey("vessels.id"))
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    space_mt = Column(Float)  # Available space in metric tons
    start_price = Column(Float)  # Price per MT at start
    current_price = Column(Float)  # Current price per MT
    min_price = Column(Float)  # Minimum acceptable price per MT
    daily_reduction = Column(Float)  # Daily price reduction amount
    status = Column(Enum(AuctionStatus), default=AuctionStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Columns for tracking total space sold
    space_sold_mt = Column(Float, default=0.0)  # Total amount of space sold
    
    # Relationships
    vessel = relationship("Vessel", back_populates="auctions")
    bids = relationship("AuctionBid", back_populates="auction", cascade="all, delete-orphan")

# Create tables
Base.metadata.create_all(bind=engine)