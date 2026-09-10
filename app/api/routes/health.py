from fastapi import APIRouter
from app.core.config import settings
from app.services.storage import storage_service

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """
    Service health check endpoint.
    """
    storage_mode = "s3" if storage_service.s3_client else "local_fallback"
    return {
        "status": "healthy",
        "environment": settings.APP_ENV,
        "storage_provider": settings.STORAGE_PROVIDER,
        "active_storage_mode": storage_mode,
        "s3_bucket": settings.AWS_S3_BUCKET_NAME if storage_mode == "s3" else None,
    }
