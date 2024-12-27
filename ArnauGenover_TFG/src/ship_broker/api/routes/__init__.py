# src/ship_broker/api/routes/__init__.py

from .vessels import router as vessels
from .cargoes import router as cargoes
from .email_processing import router as email_processing
from .test import router as test
from .matching import router as matching
from .search import router as search

__all__ = ["vessels", "cargoes", "email_processing", "test", "matching", "search"]