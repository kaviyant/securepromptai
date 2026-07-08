import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import EmailStr

class Settings(BaseSettings):
    # App General Settings
    ENV_MODE: str = "development"
    APP_NAME: str = "SecurePrompt AI Backend"
    DEBUG: bool = True
    
    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # MongoDB Settings
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "secureprompt_db"
    
    # JWT Auth Settings
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Initial Admin Setup
    SYSTEM_INIT_ADMIN_EMAIL: EmailStr = "admin@secureprompt.ai"
    SYSTEM_INIT_ADMIN_PASSWORD: str = "SecureAdmin2026!"
    
    # Proxy APIs
    GROQ_API_KEY: str = ""

    # Load from .env file
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate settings
settings = Settings()
