# src/ship_broker/core/database.py
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from ..config import settings

# Get the current directory
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
database_url = f"sqlite:///{os.path.join(current_dir, 'ship_broker.db')}"

engine = create_engine(database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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
    created_at = Column(DateTime, default=datetime.utcnow)

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

# Create all tables
Base.metadata.create_all(bind=engine)