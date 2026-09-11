# InRisk Weather Explorer - Backend API

Production-grade Python FastAPI backend for ingesting historical weather data from Open-Meteo API and storing raw JSON snapshots in **AWS S3 Cloud Object Storage**.

[![Live API](https://img.shields.io/badge/Live_API-Render/Vercel-emerald?style=flat-square&logo=fastapi)](https://weather-backend-raj.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)](https://python.org)
[![AWS S3](https://img.shields.io/badge/AWS-S3_Bucket-orange?style=flat-square&logo=amazonaws)](https://aws.amazon.com/s3)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen?style=flat-square&logo=pytest)](https://pytest.org)

---

## 🌐 Deployment Status & Live URL

- **Live API Base URL**: `https://weather-backend-raj.onrender.com` (or your deployed API endpoint)
- **Live Swagger API Docs**: `https://weather-backend-raj.onrender.com/docs`
- **Last Verified Live**: September 11, 2026
- **Redeployment on Demand**: This service is deployed on Render/Vercel free tier. If the service enters sleep mode due to inactivity, triggering any request will automatically wake the instance within 20 seconds.

---

## 🏗️ System Architecture & Design Approach

The backend follows a **layered, production-grade microservices architecture**:

```
weather-backend/
├── app/
│   ├── main.py              # FastAPI application, CORS configuration, exception handlers
│   ├── core/
│   │   └── config.py        # Pydantic BaseSettings for AWS S3 bucket, region, CORS origins
│   ├── api/
│   │   └── routes/
│   │       ├── weather.py   # Endpoints: POST /store-weather-data, GET /list-weather-files, GET /weather-file-content/{file}
│   │       └── health.py    # Endpoint: GET /health with live AWS S3 connectivity diagnostics
│   ├── schemas/
│   │   └── weather.py       # Pydantic v2 schemas (lat/lon, ISO date order, 31-day window limit)
│   └── services/
│       ├── open_meteo.py    # Async Open-Meteo API client (httpx) with forecast fallback
│       └── storage.py       # AWS S3 cloud storage service (boto3) with head_bucket check & local fallback
└── tests/
    └── test_weather.py      # Automated pytest unit test suite (6 passing tests)
```

### Key Engineering Decisions:
1. **FastAPI Engine**: Asynchronous I/O (`async/await`) handling Open-Meteo fetches and AWS S3 uploads concurrently without blocking main loops.
2. **Strict Pydantic v2 Validation**: Enforces \(\text{Latitude} \in [-90, 90]\), \(\text{Longitude} \in [-180, 180]\), ISO date format, date ordering (`start_date <= end_date`), and 31-day max range.
3. **AWS S3 Storage Abstraction**: Direct integration with AWS S3 using `boto3` SDK (`put_object`, `get_paginator('list_objects_v2')`). Automatically falls back to local storage (`/local_storage/`) if AWS credentials are unconfigured.
4. **Standardized Object Naming**: `weather_<lat>_<lon>_<start>_<end>_<timestamp>.json` enables period filtering directly from object keys without an external database index.

---

## 🛠️ Libraries & Technologies Used

- **Framework**: FastAPI (v0.109+)
- **ASGI Server**: Uvicorn (v0.27+)
- **Cloud SDK**: Boto3 (v1.34+)
- **Data Validation**: Pydantic (v2.6+) & Pydantic-Settings
- **HTTP Client**: HTTPX (v0.26+)
- **Environment**: Python-Dotenv
- **Testing**: Pytest (v8.0+) & Pytest-Asyncio

---

## ⚡ Local Setup & Execution Guide

### Prerequisites
- Python 3.11 or higher installed on your system.

### Step 1: Clone Repository & Create Virtual Environment
```bash
git clone https://github.com/rajp2026/weather-backend.git
cd weather-backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env` and fill in your AWS credentials:
```bash
cp .env.example .env
```

Edit `.env`:
```ini
# Application Settings
APP_ENV=development
DEBUG=True
PORT=8000
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000","https://*.vercel.app"]

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_REGION=us-east-1
AWS_S3_BUCKET_NAME=your_s3_bucket_name

# Storage Mode ('s3' or 'local')
STORAGE_PROVIDER=s3

# Open-Meteo API
OPEN_METEO_BASE_URL=https://archive-api.open-meteo.com/v1/archive
```

### Step 4: Start Development Server
```bash
uvicorn app.main:app --reload --port 8000
```

The API server will run locally at `http://localhost:8000`.  
Interactive Swagger API Documentation: `http://localhost:8000/docs`.

---

## 🧪 Running Automated Unit Tests

Execute the test suite using `pytest`:
```bash
python -m pytest
```
*Output:* `6 passed in 2.94s` (100% test pass rate covering validation, pagination, date limits, and 404 error cases).

---

## 📋 API Endpoint Reference

### 1. `POST /store-weather-data`
Fetch historical daily weather from Open-Meteo and store raw JSON in AWS S3.
- **Request Body**:
  ```json
  {
    "latitude": 35.6762,
    "longitude": 139.6503,
    "start_date": "2024-01-01",
    "end_date": "2024-01-07"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "status": "ok",
    "file": "weather_35.68_139.65_2024-01-01_2024-01-07_20260911_012500.json"
  }
  ```

### 2. `GET /list-weather-files`
List stored weather objects with limit, offset pagination, and date period filtering.
- **Query Params**: `limit=10&offset=0&start_date=2024-01-01&end_date=2024-01-31`
- **Response (200 OK)**:
  ```json
  {
    "files": [
      {
        "name": "weather_35.68_139.65_2024-01-01_2024-01-07_20260911_012500.json",
        "size": 1842,
        "created_at": "2026-09-11T01:25:00.000000+00:00"
      }
    ],
    "total": 1,
    "limit": 10,
    "offset": 0
  }
  ```

### 3. `GET /weather-file-content/{file}`
Fetch raw JSON content of specified weather object.
- **Response (200 OK)**: Raw Open-Meteo JSON payload.
- **Response (404 Not Found)**: `{"status": "error", "message": "not found"}`

### 4. `GET /health`
Service health check and live AWS S3 connectivity status.
- **Response (200 OK)**: `{"status": "healthy", "active_storage_mode": "s3", ...}`

---


