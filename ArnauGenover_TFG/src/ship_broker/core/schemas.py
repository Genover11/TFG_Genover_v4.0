# src/ship_broker/core/schemas.py

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class VesselBase(BaseModel):
    name: str
    vessel_type: Optional[str] = None
    dwt: Optional[float] = None
    position: Optional[str] = None
    eta: Optional[datetime] = None
    description: Optional[str] = None

class VesselCreate(VesselBase):
    pass

class Vessel(VesselBase):
    id: int
    last_updated: Optional[datetime] = None

    class Config:
        from_attributes = True

class VesselSearch(BaseModel):
    name: Optional[str] = None
    vessel_type: Optional[str] = None
    position: Optional[str] = None
    min_dwt: Optional[float] = None
    max_dwt: Optional[float] = None

class CargoBase(BaseModel):
    cargo_type: str
    quantity: float
    load_port: str
    discharge_port: Optional[str] = None  # Made optional
    laycan_start: Optional[datetime] = None
    laycan_end: Optional[datetime] = None
    description: Optional[str] = None
    rate: Optional[str] = None  # Added rate field

class CargoCreate(CargoBase):
    pass

class CargoResponse(CargoBase):
    id: int
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    class Config:
        from_attributes = True

class Cargo(CargoBase):
    id: int
    last_updated: Optional[datetime] = None

    class Config:
        from_attributes = True

class CargoSearch(BaseModel):
    cargo_type: Optional[str] = None
    load_port: Optional[str] = None
    discharge_port: Optional[str] = None
    min_quantity: Optional[float] = None
    max_quantity: Optional[float] = None

class Email(BaseModel):
    sender: str
    subject: str
    body: str
    received_date: datetime