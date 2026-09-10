import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.health import router as health_router
from app.api.routes.weather import router as weather_router
from app.core.config import settings

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("weather_app")

app = FastAPI(
    title="InRisk Weather Explorer API",
    description="Backend API for fetching historical weather data, storing in AWS S3, and providing climate visualization endpoints.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Bulletproof CORS middleware configuration for production deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Validation Exception Handler for clear 400 response formatting
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    error_msg = errors[0].get("msg", "Validation error") if errors else "Invalid request payload"
    if "Value error, " in error_msg:
        error_msg = error_msg.replace("Value error, ", "")
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"status": "error", "message": error_msg},
    )


# Include Routers
app.include_router(health_router)
app.include_router(weather_router)


@app.get("/")
async def root():
    return {
        "name": "InRisk Weather Explorer API",
        "version": "1.0.0",
        "documentation": "/docs",
    }
