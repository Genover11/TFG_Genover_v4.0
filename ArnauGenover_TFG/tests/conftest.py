
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import Generator

from ship_broker.main import app
from ship_broker.core.database import Base, engine
from ship_broker.api.dependencies import get_db

@pytest.fixture
def test_db():
    # Create test database
    Base.metadata.create_all(bind=engine)
    try:
        db = Session(engine)
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            test_db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides = {}