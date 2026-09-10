import logging
import httpx
from fastapi import HTTPException
from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenMeteoService:
    def __init__(self):
        self.base_url = settings.OPEN_METEO_BASE_URL

    async def fetch_historical_weather(
        self, latitude: float, longitude: float, start_date: str, end_date: str
    ) -> dict:
        """
        Fetches historical daily weather variables from Open-Meteo API.
        Variables requested:
          - temperature_2m_max
          - temperature_2m_min
          - apparent_temperature_max
          - apparent_temperature_min
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "apparent_temperature_max",
                "apparent_temperature_min",
            ],
            "timezone": "auto",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.get(self.base_url, params=params)
                
                # If archive API fails due to recent date range, fallback to standard forecast API
                if response.status_code != 200:
                    logger.warning(
                        f"Archive API returned status {response.status_code}, trying forecast endpoint."
                    )
                    fallback_url = "https://api.open-meteo.com/v1/forecast"
                    response = await client.get(fallback_url, params=params)

                if response.status_code != 200:
                    logger.error(f"Open-Meteo API error: {response.text}")
                    raise HTTPException(
                        status_code=502,
                        detail=f"Failed to fetch weather data from Open-Meteo API: {response.text}",
                    )

                data = response.json()
                return data

            except httpx.RequestError as exc:
                logger.error(f"HTTP connection error with Open-Meteo: {exc}")
                raise HTTPException(
                    status_code=503,
                    detail=f"Network error connecting to Open-Meteo API: {str(exc)}",
                )


open_meteo_service = OpenMeteoService()
