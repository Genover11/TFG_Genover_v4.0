# src/ship_broker/core/database.py
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from ..config import settings

engine = create_engine(settings.SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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

# Create tables
Base.metadata.create_all(bind=engine)