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

def print_database_contents():
    """Utility function to print all database contents"""
    db = SessionLocal()
    try:
        print("\n=== VESSELS ===")
        vessels = db.query(Vessel).all()
        for vessel in vessels:
            print(f"Name: {vessel.name}")
            print(f"Type: {vessel.vessel_type}")
            print(f"Position: {vessel.position}")
            print(f"DWT: {vessel.dwt}")
            print("-" * 20)

        print("\n=== CARGOES ===")
        cargoes = db.query(Cargo).all()
        for cargo in cargoes:
            print(f"Type: {cargo.cargo_type}")
            print(f"Quantity: {cargo.quantity}")
            print(f"Route: {cargo.load_port} -> {cargo.discharge_port}")
            print("-" * 20)
    finally:
        db.close()

# Add a new route to view database contents
def get_db_stats():
    """Get database statistics"""
    db = SessionLocal()
    try:
        vessel_count = db.query(Vessel).count()
        cargo_count = db.query(Cargo).count()
        return {
            "vessels_count": vessel_count,
            "cargoes_count": cargo_count,
            "last_update": datetime.now().isoformat()
        }
    finally:
        db.close()