import json
import os
from pathlib import Path
from typing import List, Union
from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Explicitly load .env file if it exists, otherwise ignore gracefully
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
load_dotenv()  # Fallback to current working directory .env


class Settings(BaseSettings):
    APP_ENV: str = "production"
    DEBUG: bool = False
    PORT: int = 8000
    CORS_ORIGINS: Union[List[str], str] = [
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

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("[") and v_str.endswith("]"):
                try:
                    return json.loads(v_str)
                except Exception:
                    pass
            return [i.strip() for i in v_str.split(",") if i.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


try:
    settings = Settings()
except Exception as err:
    # Graceful fallback settings if environment parsing fails in serverless
    class FallbackSettings:
        APP_ENV = "production"
        DEBUG = False
        PORT = 8000
        CORS_ORIGINS = ["*"]
        AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
        AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
        AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
        AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME", "inrisk-weather-data-raj")
        STORAGE_PROVIDER = os.getenv("STORAGE_PROVIDER", "s3")
        OPEN_METEO_BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
    settings = FallbackSettings()
