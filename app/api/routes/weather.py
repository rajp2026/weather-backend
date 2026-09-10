from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.schemas.weather import (
    StoreWeatherDataRequest,
    StoreWeatherDataResponse,
    ListWeatherFilesResponse,
    ErrorResponse,
)
from app.services.open_meteo import open_meteo_service
from app.services.storage import storage_service

router = APIRouter(tags=["Weather Explorer"])


@router.post(
    "/store-weather-data",
    response_model=StoreWeatherDataResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid Input Validation Error"},
        502: {"model": ErrorResponse, "description": "External API Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
async def store_weather_data(payload: StoreWeatherDataRequest):
    """
    1. Validates inputs (latitude, longitude, date ranges).
    2. Calls Open-Meteo daily-history API.
    3. Stores raw JSON response into AWS S3 bucket.
    4. Returns stored filename.
    """
    # Fetch data from Open-Meteo
    raw_weather_data = await open_meteo_service.fetch_historical_weather(
        latitude=payload.latitude,
        longitude=payload.longitude,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )

    # Generate standardized filename
    filename = storage_service.generate_filename(
        lat=payload.latitude,
        lon=payload.longitude,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )

    # Save to AWS S3 (or local fallback)
    stored_name = storage_service.store_weather_json(filename, raw_weather_data)

    return StoreWeatherDataResponse(status="ok", file=stored_name)


@router.get(
    "/list-weather-files",
    response_model=ListWeatherFilesResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Validation Error"},
    },
)
async def list_weather_files(
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of files to return"),
    offset: int = Query(default=0, ge=0, description="Offset index for pagination"),
    start_date: Optional[str] = Query(default=None, description="Filter files starting on or after YYYY-MM-DD"),
    end_date: Optional[str] = Query(default=None, description="Filter files ending on or before YYYY-MM-DD"),
):
    """
    Lists stored weather JSON objects from the cloud object storage bucket with pagination and optional date period filtering.
    """
    # Validate date formats and ranges if provided
    if start_date and end_date:
        try:
            s_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            e_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": "error", "message": "Dates must be in valid YYYY-MM-DD format"},
            )

        if s_dt > e_dt:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": "error", "message": "start_date must be less than or equal to end_date"},
            )

        day_diff = (e_dt - s_dt).days + 1
        if day_diff > 31:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": "error", "message": "Date period filter range cannot exceed 31 days"},
            )

    files_list, total_count = storage_service.list_weather_files(
        limit=limit,
        offset=offset,
        start_date=start_date,
        end_date=end_date,
    )
    return ListWeatherFilesResponse(
        files=files_list,
        total=total_count,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/weather-file-content/{file}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "File Not Found"},
    },
)
async def get_weather_file_content(file: str):
    """
    Fetches raw JSON content of specified weather file from storage bucket.
    Returns 404 with {"status": "error", "message": "not found"} if file is missing.
    """
    content = storage_service.get_weather_file_content(file)
    if content is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"status": "error", "message": "not found"},
        )
    return content
