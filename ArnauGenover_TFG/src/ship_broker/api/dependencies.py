# src/ship_broker/api/dependencies.py
from typing import Generator
import logging
from ..core.database import SessionLocal

logger = logging.getLogger(__name__)

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        db.close()