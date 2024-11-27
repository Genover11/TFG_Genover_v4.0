# src/ship_broker/init_db.py
import os
import sys
from pathlib import Path

# Get the absolute path to the src directory
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent.parent / "src"
sys.path.append(str(src_dir))

from ship_broker.core.database import Base, engine
from ship_broker.config import settings

def init_db():
    # Create the database directory if it doesn't exist
    db_path = Path(settings.SQLALCHEMY_DATABASE_URL.replace('sqlite:///', ''))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    print(f"Database tables created successfully at {db_path}!")

if __name__ == "__main__":
    try:
        init_db()
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        sys.exit(1)