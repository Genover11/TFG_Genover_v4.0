# src/ship_broker/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_NAME: str = "Ship Broker"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    SQLALCHEMY_DATABASE_URL: str = "sqlite:///./src/ship_broker/ship_broker.db"
    
    # Email settings
    EMAIL_ADDRESS: str = ""
    EMAIL_PASSWORD: str = ""
    IMAP_SERVER: str = "imap.gmail.com"
    
    # OpenAI API
    OPENAI_API_KEY: str = ""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()