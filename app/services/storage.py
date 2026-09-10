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
    when S3 bucket is unconfigured or credentials are absent/invalid.
    """

    def __init__(self):
        self.local_dir = Path("local_storage")
        try:
            self.local_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Use writable /tmp directory in serverless environments (e.g. Vercel / AWS Lambda)
            self.local_dir = Path("/tmp/local_storage")
            self.local_dir.mkdir(parents=True, exist_ok=True)

        self.s3_client = None
        self.s3_init_error = None
        self.bucket_name = ""
        self.region = ""
        self.provider = ""
        
        self.init_storage()

    def init_storage(self):
        """Initializes or re-initializes S3 storage connection."""
        self.bucket_name = settings.AWS_S3_BUCKET_NAME
        self.region = settings.AWS_REGION
        self.provider = settings.STORAGE_PROVIDER.lower()
        self.s3_client = None
        self.s3_init_error = None

        key_id = settings.AWS_ACCESS_KEY_ID.strip()
        secret_key = settings.AWS_SECRET_ACCESS_KEY.strip()

        if self.provider == "s3" and key_id and secret_key:
            try:
                client = boto3.client(
                    "s3",
                    aws_access_key_id=key_id,
                    aws_secret_access_key=secret_key,
                    region_name=self.region,
                )
                # Verify bucket connectivity & permissions via head_bucket
                client.head_bucket(Bucket=self.bucket_name)
                self.s3_client = client
                logger.info(f"Successfully connected to AWS S3 bucket '{self.bucket_name}' in region '{self.region}'")
            except ClientError as e:
                err_code = e.response.get("Error", {}).get("Code", str(e))
                err_msg = e.response.get("Error", {}).get("Message", str(e))
                self.s3_init_error = f"AWS S3 Error ({err_code}): {err_msg}"
                logger.error(f"S3 Connection Failed: {self.s3_init_error}")
                self.s3_client = None
            except Exception as e:
                self.s3_init_error = f"Initialization Error: {str(e)}"
                logger.error(f"S3 Client Exception: {self.s3_init_error}")
                self.s3_client = None
        else:
            missing_reason = []
            if not key_id:
                missing_reason.append("AWS_ACCESS_KEY_ID is missing")
            if not secret_key:
                missing_reason.append("AWS_SECRET_ACCESS_KEY is missing")
            if self.provider != "s3":
                missing_reason.append(f"STORAGE_PROVIDER is set to '{self.provider}'")
            
            self.s3_init_error = ", ".join(missing_reason)
            logger.info(f"S3 not enabled ({self.s3_init_error}). Using local storage fallback.")

    def generate_filename(self, lat: float, lon: float, start_date: str, end_date: str) -> str:
        """
        Formats filename according to standard:
        weather_<lat>_<lon>_<start>_<end>_<timestamp>.json
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        lat_str = f"{lat:.2f}"
        lon_str = f"{lon:.2f}"
        return f"weather_{lat_str}_{lon_str}_{start_date}_{end_date}_{timestamp}.json"

    def _parse_dates_from_filename(self, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """Parses start_date and end_date embedded in filename format weather_<lat>_<lon>_<start>_<end>_<timestamp>.json"""
        try:
            parts = filename.replace(".json", "").split("_")
            if len(parts) >= 5 and parts[0] == "weather":
                return parts[3], parts[4]
        except Exception:
            pass
        return None, None

    def store_weather_json(self, filename: str, data: dict) -> str:
        """
        Stores the raw JSON dictionary into AWS S3 (or local fallback).
        """
        json_bytes = json.dumps(data, indent=2).encode("utf-8")

        if not self.s3_client:
            self.init_storage()

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
                self.s3_init_error = f"Upload error: {str(e)}"

        # Local fallback execution
        file_path = self.local_dir / filename
        with open(file_path, "wb") as f:
            f.write(json_bytes)
        logger.info(f"Stored {filename} to local storage fallback at {file_path}")
        return filename

    def list_weather_files(
        self,
        limit: int = 50,
        offset: int = 0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Lists stored weather files in AWS S3 or local directory with pagination and optional date period filtering.
        Returns Tuple: (paginated_files_list, total_file_count)
        """
        all_files = []

        if not self.s3_client:
            self.init_storage()

        if self.s3_client:
            try:
                paginator = self.s3_client.get_paginator('list_objects_v2')
                page_iterator = paginator.paginate(Bucket=self.bucket_name)
                
                for page in page_iterator:
                    for obj in page.get("Contents", []):
                        key = obj["Key"]
                        if key.endswith(".json"):
                            all_files.append({
                                "name": key,
                                "size": obj["Size"],
                                "created_at": obj["LastModified"].isoformat(),
                            })
            except (BotoCoreError, ClientError) as e:
                logger.error(f"S3 list objects error: {e}. Listing from local storage fallback.")
                all_files = []

        # Local fallback listing if S3 is inactive or empty fallback
        if not self.s3_client:
            for file_path in self.local_dir.glob("*.json"):
                stat = file_path.stat()
                created_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                all_files.append({
                    "name": file_path.name,
                    "size": stat.st_size,
                    "created_at": created_at,
                })
        
        all_files.sort(key=lambda x: x["created_at"], reverse=True)

        # Apply specific date period filtering if requested
        if start_date or end_date:
            filtered = []
            for item in all_files:
                f_start, f_end = self._parse_dates_from_filename(item["name"])
                if f_start and f_end:
                    match_start = (not start_date) or (f_start >= start_date)
                    match_end = (not end_date) or (f_end <= end_date)
                    if match_start and match_end:
                        filtered.append(item)
                else:
                    filtered.append(item)
            all_files = filtered

        total = len(all_files)
        paginated_files = all_files[offset : offset + limit]
        return paginated_files, total

    def get_weather_file_content(self, filename: str) -> Optional[dict]:
        """
        Fetches raw weather JSON content from AWS S3 or local storage fallback.
        Returns dict or None if file not found.
        """
        clean_filename = os.path.basename(filename)

        if not self.s3_client:
            self.init_storage()

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
