from datetime import date, datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, model_validator


class StoreWeatherDataRequest(BaseModel):
    latitude: float = Field(..., description="Latitude coordinate between -90.0 and 90.0")
    longitude: float = Field(..., description="Longitude coordinate between -180.0 and 180.0")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")

    @model_validator(mode="after")
    def validate_inputs(self):
        # Validate Latitude range
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError("Latitude must be within range [-90, 90]")

        # Validate Longitude range
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError("Longitude must be within range [-180, 180]")

        # Validate Date format
        try:
            start_dt = datetime.strptime(self.start_date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("start_date must be a valid date in YYYY-MM-DD format")

        try:
            end_dt = datetime.strptime(self.end_date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("end_date must be a valid date in YYYY-MM-DD format")

        # Check date order
        if start_dt > end_dt:
            raise ValueError("start_date must be less than or equal to end_date")

        # Check max date range limit (<= 31 days)
        day_count = (end_dt - start_dt).days + 1
        if day_count > 31:
            raise ValueError("Date range exceeds the maximum limit of 31 days")

        return self


class StoreWeatherDataResponse(BaseModel):
    status: str = "ok"
    file: str


class WeatherFileInfo(BaseModel):
    name: str
    size: int
    created_at: str


class ListWeatherFilesResponse(BaseModel):
    files: List[WeatherFileInfo]


class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
