# src/ship_broker/api/routes/__init__.py
from .vessels import router as vessels
from .cargoes import router as cargoes
from .email_processing import router as email_processing

__all__ = ["vessels", "cargoes", "email_processing"]