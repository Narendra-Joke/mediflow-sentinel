from fastapi.testclient import TestClient

from src.api import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_critical_risk_endpoint():
    payload = {
        "facility_id": "TEST-API-A",
        "medicine": "Medicine-A",
        "stock": 20,
        "daily_usage": 15,
        "safety_stock": 30,
        "incoming_stock": 0,
        "delivery_delay_days": 2,
    }

    response = client.post("/inventory/assess", json=payload)

    assert response.status_code == 200
    assert response.json()["risk"] == "CRITICAL"
    assert response.json()["days_until_stockout"] == 1.33


def test_high_risk_endpoint():
    payload = {
        "facility_id": "TEST-API-B",
        "medicine": "Medicine-B",
        "stock": 12,
        "daily_usage": 4,
        "safety_stock": 10,
        "incoming_stock": 0,
        "delivery_delay_days": 0,
    }

    response = client.post("/inventory/assess", json=payload)

    assert response.status_code == 200
    assert response.json()["risk"] == "HIGH"


def test_medium_risk_endpoint():
    payload = {
        "facility_id": "TEST-API-D",
        "medicine": "Medicine-D",
        "stock": 80,
        "daily_usage": 20,
        "safety_stock": 10,
        "incoming_stock": 0,
        "delivery_delay_days": 0,
    }

    response = client.post("/inventory/assess", json=payload)

    assert response.status_code == 200
    assert response.json()["risk"] == "MEDIUM"


def test_low_risk_endpoint():
    payload = {
        "facility_id": "TEST-API-C",
        "medicine": "Medicine-C",
        "stock": 200,
        "daily_usage": 20,
        "safety_stock": 50,
        "incoming_stock": 0,
        "delivery_delay_days": 2,
    }

    response = client.post("/inventory/assess", json=payload)

    assert response.status_code == 200
    assert response.json()["risk"] == "LOW"


def test_zero_usage_endpoint():
    payload = {
        "facility_id": "TEST-API-E",
        "medicine": "Medicine-E",
        "stock": 100,
        "daily_usage": 0,
        "safety_stock": 10,
        "incoming_stock": 0,
        "delivery_delay_days": 2,
    }

    response = client.post("/inventory/assess", json=payload)

    assert response.status_code == 200
    assert response.json()["risk"] == "LOW"
    assert response.json()["days_until_stockout"] is None


def test_negative_stock_is_rejected_by_api():
    payload = {
        "facility_id": "TEST-API-F",
        "medicine": "Medicine-F",
        "stock": -1,
        "daily_usage": 10,
        "safety_stock": 5,
        "incoming_stock": 0,
        "delivery_delay_days": 2,
    }

    response = client.post("/inventory/assess", json=payload)

    assert response.status_code == 422
