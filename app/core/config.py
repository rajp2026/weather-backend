import os
from pathlib import Path
from typing import List, Union
from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Explicitly load .env file from root backend folder
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()  # Fallback to current working directory .env


class Settings(BaseSettings):
    APP_ENV: str = "production"
    DEBUG: bool = False
    PORT: int = 8000
    CORS_ORIGINS: List[str] = [
        "https://weather-frontend-topaz-ten.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # AWS Credentials & Bucket
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    AWS_S3_BUCKET_NAME: str = "inrisk-weather-data-raj"

    # Storage provider: 's3' or 'local'
    STORAGE_PROVIDER: str = "s3"

    # Open-Meteo API
    OPEN_METEO_BASE_URL: str = "https://archive-api.open-meteo.com/v1/archive"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
