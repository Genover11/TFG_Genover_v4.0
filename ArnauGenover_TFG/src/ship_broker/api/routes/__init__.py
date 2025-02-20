# src/ship_broker/api/routes/__init__.py

from .vessels import router as vessels
from .cargoes import router as cargoes
from .email_processing import router as email_processing
from .test import router as test
from .matching import router as matching
from .auctions import router as auctions
from .auth import router as auth

# Create references to the routers
vessels.router = vessels
cargoes.router = cargoes
email_processing.router = email_processing
test.router = test
matching.router = matching
auctions.router = auctions
auth.router = auth

__all__ = [
    "vessels", 
    "cargoes", 
    "email_processing", 
    "test", 
    "matching",
    "auctions",
    "auth"
]