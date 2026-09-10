import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_invalid_latitude():
    payload = {
        "latitude": 100.0,  # Invalid (> 90)
        "longitude": 40.0,
        "start_date": "2024-01-01",
        "end_date": "2024-01-10",
    }
    response = client.post("/store-weather-data", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"
    assert "Latitude must be within range" in data["message"]


def test_invalid_date_order():
    payload = {
        "latitude": 35.6762,
        "longitude": 139.6503,
        "start_date": "2024-01-10",
        "end_date": "2024-01-01",  # Invalid (end < start)
    }
    response = client.post("/store-weather-data", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"
    assert "start_date must be less than or equal to end_date" in data["message"]


def test_date_range_exceeds_limit():
    payload = {
        "latitude": 35.6762,
        "longitude": 139.6503,
        "start_date": "2024-01-01",
        "end_date": "2024-02-15",  # Invalid (> 31 days)
    }
    response = client.post("/store-weather-data", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"
    assert "Date range exceeds the maximum limit of 31 days" in data["message"]


def test_get_non_existent_file():
    response = client.get("/weather-file-content/non_existent_weather_file_9999.json")
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "not found"


def test_list_weather_files():
    response = client.get("/list-weather-files")
    assert response.status_code == 200
    data = response.json()
    assert "files" in data
    assert isinstance(data["files"], list)
