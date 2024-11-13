# core/schemas.py
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class VesselBase(BaseModel):
    name: str
    dwt: Optional[float] = None
    position: Optional[str] = None
    eta: Optional[datetime] = None
    open_date: Optional[datetime] = None
    vessel_type: Optional[str] = None
    description: str

class VesselCreate(VesselBase):
    pass

class Vessel(VesselBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)  # This replaces orm_mode = True

class CargoBase(BaseModel):
    cargo_type: str
    quantity: Optional[float] = None
    load_port: Optional[str] = None
    discharge_port: Optional[str] = None
    laycan_start: Optional[datetime] = None
    laycan_end: Optional[datetime] = None
    rate: Optional[str] = None
    description: str

class CargoCreate(CargoBase):
    pass

class Cargo(CargoBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)  # This replaces orm_mode = True