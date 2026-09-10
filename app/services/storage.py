import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """
    AWS S3 Cloud Storage Service with transparent local fallback
    when S3 bucket is unconfigured or credentials are absent.
    """

    def __init__(self):
        self.bucket_name = settings.AWS_S3_BUCKET_NAME
        self.region = settings.AWS_REGION
        self.provider = settings.STORAGE_PROVIDER.lower()
        self.s3_client = None
        self.local_dir = Path("local_storage")

        if self.provider == "s3" and settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            try:
                self.s3_client = boto3.client(
                    "s3",
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=self.region,
                )
                logger.info(f"Initialized AWS S3 storage client for bucket '{self.bucket_name}'")
            except Exception as e:
                logger.warning(f"Failed to initialize S3 client: {e}. Falling back to local storage.")
                self.s3_client = None
        else:
            logger.info("AWS credentials not provided or STORAGE_PROVIDER != 's3'. Using local storage fallback.")

        # Ensure local fallback directory exists
        self.local_dir.mkdir(parents=True, exist_ok=True)

    def generate_filename(self, lat: float, lon: float, start_date: str, end_date: str) -> str:
        """
        Formats filename according to standard:
        weather_<lat>_<lon>_<start>_<end>_<timestamp>.json
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        # Format lat/lon cleanly (replace minus signs with 'neg' or keep standard)
        lat_str = f"{lat:.2f}"
        lon_str = f"{lon:.2f}"
        return f"weather_{lat_str}_{lon_str}_{start_date}_{end_date}_{timestamp}.json"

    def store_weather_json(self, filename: str, data: dict) -> str:
        """
        Stores the raw JSON dictionary into AWS S3 (or local fallback).
        """
        json_bytes = json.dumps(data, indent=2).encode("utf-8")
        
        if self.s3_client:
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=filename,
                    Body=json_bytes,
                    ContentType="application/json",
                )
                logger.info(f"Successfully uploaded {filename} to AWS S3 bucket {self.bucket_name}")
                return filename
            except (BotoCoreError, ClientError) as e:
                logger.error(f"S3 upload error: {e}. Saving to local storage fallback.")

        # Local fallback execution
        file_path = self.local_dir / filename
        with open(file_path, "wb") as f:
            f.write(json_bytes)
        logger.info(f"Stored {filename} to local storage fallback at {file_path}")
        return filename

    def list_weather_files(self) -> List[Dict[str, Any]]:
        """
        Lists stored weather files in AWS S3 or local directory.
        Returns list of dicts: [{"name": str, "size": int, "created_at": ISO8601 str}]
        """
        files = []

        if self.s3_client:
            try:
                response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
                contents = response.get("Contents", [])
                for obj in contents:
                    key = obj["Key"]
                    if key.endswith(".json"):
                        files.append({
                            "name": key,
                            "size": obj["Size"],
                            "created_at": obj["LastModified"].isoformat(),
                        })
                # Sort newest first
                files.sort(key=lambda x: x["created_at"], reverse=True)
                return files
            except (BotoCoreError, ClientError) as e:
                logger.error(f"S3 list objects error: {e}. Listing from local storage fallback.")

        # Local fallback listing
        for file_path in self.local_dir.glob("*.json"):
            stat = file_path.stat()
            created_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            files.append({
                "name": file_path.name,
                "size": stat.st_size,
                "created_at": created_at,
            })
        
        files.sort(key=lambda x: x["created_at"], reverse=True)
        return files

    def get_weather_file_content(self, filename: str) -> Optional[dict]:
        """
        Fetches raw weather JSON content from AWS S3 or local storage fallback.
        Returns dict or None if file not found.
        """
        # Sanitize filename to prevent path traversal
        clean_filename = os.path.basename(filename)

        if self.s3_client:
            try:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=clean_filename)
                body_str = response["Body"].read().decode("utf-8")
                return json.loads(body_str)
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    logger.warning(f"File {clean_filename} not found in AWS S3 bucket.")
                    return None
                logger.error(f"S3 get_object error: {e}")
            except Exception as e:
                logger.error(f"Unexpected S3 error: {e}")

        # Local fallback retrieval
        file_path = self.local_dir / clean_filename
        if file_path.exists() and file_path.is_file():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading local file {clean_filename}: {e}")
                return None

        return None


storage_service = StorageService()
