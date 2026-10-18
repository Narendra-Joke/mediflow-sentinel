from fastapi.testclient import TestClient
import pytest

from src.api import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolate_audit_log(tmp_path, monkeypatch):
    import src.api as api

    monkeypatch.setattr(
        api, "AUDIT_LOG_PATH", tmp_path / "audit_events.jsonl"
    )



@pytest.fixture
def isolate_genai_jobs(tmp_path, monkeypatch):
    import src.genai_jobs as genai_jobs

    monkeypatch.setattr(
        genai_jobs, "JOB_DIR", tmp_path / "genai-jobs"
    )


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


def test_incoming_stock_updates_projected_coverage():
    payload = {
        "facility_id": "TEST-API-G",
        "medicine": "Medicine-G",
        "stock": 20,
        "daily_usage": 10,
        "safety_stock": 5,
        "incoming_stock": 100,
        "delivery_delay_days": 1,
    }

    response = client.post("/inventory/assess", json=payload)

    assert response.status_code == 200

    result = response.json()
    assert result["risk"] == "LOW"
    assert result["days_until_stockout"] == 2.0
    assert result["projected_days_until_stockout"] == 12.0


def test_events_endpoint_returns_newest_first(tmp_path, monkeypatch):
    import json
    import src.api as api

    log_path = tmp_path / "events.jsonl"
    events = [
        {
            "event_type": "MEDICINE_DISPENSED",
            "facility_id": "CLINIC-A",
            "medicine": "Amoxicillin",
            "simulated_day": 1,
        },
        {
            "event_type": "RISK_TRANSITION",
            "facility_id": "CLINIC-A",
            "medicine": "Amoxicillin",
            "previous_risk": "HIGH",
            "risk": "CRITICAL",
            "simulated_day": 2,
        },
    ]
    log_path.write_text(
        "\n".join(json.dumps(event) for event in events) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(api, "AUDIT_LOG_PATH", log_path)

    response = client.get("/events")

    assert response.status_code == 200
    result = response.json()
    assert result["count"] == 2
    assert result["events"][0]["simulated_day"] == 2
    assert result["events"][1]["simulated_day"] == 1


def test_transition_endpoint_filters_by_facility_and_medicine(
    tmp_path, monkeypatch
):
    import json
    import src.api as api

    log_path = tmp_path / "events.jsonl"
    events = [
        {
            "event_type": "RISK_TRANSITION",
            "facility_id": "CLINIC-A",
            "medicine": "Amoxicillin",
            "previous_risk": "HIGH",
            "risk": "CRITICAL",
        },
        {
            "event_type": "RISK_TRANSITION",
            "facility_id": "CLINIC-B",
            "medicine": "Paracetamol",
            "previous_risk": "LOW",
            "risk": "MEDIUM",
        },
        {
            "event_type": "MEDICINE_DISPENSED",
            "facility_id": "CLINIC-A",
            "medicine": "Amoxicillin",
        },
    ]
    log_path.write_text(
        "\n".join(json.dumps(event) for event in events) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(api, "AUDIT_LOG_PATH", log_path)

    response = client.get(
        "/events/transitions",
        params={
            "facility_id": "CLINIC-A",
            "medicine": "Amoxicillin",
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["count"] == 1
    assert result["events"][0]["risk"] == "CRITICAL"


def test_events_endpoint_respects_limit(tmp_path, monkeypatch):
    import json
    import src.api as api

    log_path = tmp_path / "events.jsonl"
    events = [
        {"event_type": "TEST", "simulated_day": day}
        for day in range(1, 4)
    ]
    log_path.write_text(
        "\n".join(json.dumps(event) for event in events) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(api, "AUDIT_LOG_PATH", log_path)

    response = client.get("/events", params={"limit": 2})

    assert response.status_code == 200
    result = response.json()
    assert result["count"] == 2
    assert [event["simulated_day"] for event in result["events"]] == [3, 2]


def test_events_endpoint_handles_missing_log(tmp_path, monkeypatch):
    import src.api as api

    monkeypatch.setattr(
        api, "AUDIT_LOG_PATH", tmp_path / "missing.jsonl"
    )

    response = client.get("/events")

    assert response.status_code == 200
    assert response.json() == {"count": 0, "events": []}


def test_events_endpoint_rejects_invalid_limit():
    response = client.get("/events", params={"limit": 0})

    assert response.status_code == 422


def test_manual_assessment_is_recorded_not_as_transition():
    payload = {
        "facility_id": "TEST-MANUAL",
        "medicine": "TestMedicine",
        "stock": 100,
        "daily_usage": 10,
        "safety_stock": 20,
        "incoming_stock": 0,
        "delivery_delay_days": 0,
    }

    response = client.post("/inventory/assess", json=payload)

    assert response.status_code == 200
    result = response.json()

    events_response = client.get("/events", params={"limit": 10})
    assert events_response.status_code == 200
    events = events_response.json()["events"]

    manual_events = [
        event for event in events
        if event["event_type"] == "MANUAL_ASSESSMENT"
    ]

    assert len(manual_events) == 1
    assert manual_events[0]["facility_id"] == "TEST-MANUAL"
    assert manual_events[0]["medicine"] == "TestMedicine"
    assert manual_events[0]["risk"] == result["risk"]
    assert "timestamp" in manual_events[0]

    transitions = client.get("/events/transitions")
    assert transitions.status_code == 200
    assert transitions.json()["count"] == 0


def test_genai_submission_creates_pending_job(isolate_genai_jobs):
    response = client.post(
        "/genai/explanations",
        json={"assessment": {"risk": "HIGH", "medicine": "TestMedicine"}},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"
    assert len(data["job_id"]) == 32

    import src.genai_jobs as genai_jobs
    request_file = genai_jobs.JOB_DIR / f"request_{data['job_id']}.json"
    assert request_file.is_file()


def test_genai_job_pending_status(isolate_genai_jobs):
    submission = client.post(
        "/genai/explanations",
        json={"assessment": {"risk": "HIGH"}},
    )
    job_id = submission.json()["job_id"]

    response = client.get(f"/genai/explanations/{job_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_genai_job_completed_status(isolate_genai_jobs):
    import json
    import src.genai_jobs as genai_jobs

    job_id = "a" * 32
    genai_jobs.JOB_DIR.mkdir(parents=True, exist_ok=True)
    result = {
        "job_id": job_id,
        "status": "completed",
        "answer": "Inventory risk is high.",
    }
    (genai_jobs.JOB_DIR / f"result_{job_id}.json").write_text(
        json.dumps(result), encoding="utf-8"
    )

    response = client.get(f"/genai/explanations/{job_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["answer"] == "Inventory risk is high."


def test_genai_job_rejects_invalid_id():
    response = client.get("/genai/explanations/not-a-valid-id")

    assert response.status_code == 400


def test_genai_job_returns_404_when_unknown(isolate_genai_jobs):
    response = client.get(f"/genai/explanations/{'b' * 32}")

    assert response.status_code == 404
