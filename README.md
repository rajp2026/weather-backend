# InRisk Weather Explorer - Backend API (AWS S3 + FastAPI)

Production-grade Python FastAPI backend for fetching historical climate/weather data from Open-Meteo API and persisting snapshots to **AWS S3 object storage**.

## 🚀 Features
- **Input Validation**: Enforces latitude \([-90, 90]\), longitude \([-180, 180]\), valid ISO dates (`start_date <= end_date`), and max 31-day date range limits.
- **Cloud Storage Integration**: Direct AWS S3 integration using `boto3` SDK with standardized file naming pattern (`weather_<lat>_<lon>_<start>_<end>_<timestamp>.json`).
- **Resilient Fallback**: Automatic local storage fallback if AWS credentials are omitted during development/testing.
- **REST API Endpoints**:
  - `POST /store-weather-data`
  - `GET /list-weather-files`
  - `GET /weather-file-content/{file}`
  - `GET /health`

## 🛠️ Tech Stack
- **Framework**: Python 3.11+ / FastAPI
- **Cloud Storage**: AWS S3 (`boto3` SDK)
- **HTTP Client**: `httpx` (async)
- **Validation**: Pydantic v2
- **Testing**: `pytest` / `TestClient`

## 📦 Local Setup

```bash
# Create python virtual environment
python -m venv venv
# Activate virtual environment (Windows)
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Run FastAPI server
uvicorn app.main:app --reload --port 8000
```

Swagger API Documentation is available at `http://localhost:8000/docs`.

## 🧪 Running Tests

```bash
pytest
```
