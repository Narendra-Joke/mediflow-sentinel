from datetime import datetime, timezone
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from src.audit import AuditLogger
from src.inventory import Inventory
from src.genai_jobs import get_explanation_status, submit_explanation
from src.predictive import predict_stockout_probability, train_model

@lru_cache(maxsize=1)
def get_predictive_model():
    return train_model()[0]

PREDICTION_NOTE = (
    "Experimental estimate trained on synthetic data; "
    "not validated on real inventory data."
)

app = FastAPI(
    title="Mediflow Sentinel API",
    description="Medicine inventory risk assessment service",
    version="1.0.0",
)

AUDIT_LOG_PATH = Path("data/audit_events.jsonl")


class InventoryRequest(BaseModel):
    facility_id: str = Field(min_length=1)
    medicine: str = Field(min_length=1)
    stock: int = Field(ge=0)
    daily_usage: float = Field(ge=0)
    safety_stock: int = Field(ge=0)
    incoming_stock: int = Field(default=0, ge=0)
    delivery_delay_days: float = Field(default=0.0, ge=0)

    @field_validator("facility_id", "medicine")
    @classmethod
    def validate_non_empty_names(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value


class GenAIExplanationRequest(BaseModel):
    assessment: dict[str, Any]


@app.post("/genai/explanations", status_code=202)
def create_genai_explanation(payload: GenAIExplanationRequest):
    job_id = submit_explanation(payload.assessment)
    return {"job_id": job_id, "status": "pending"}


@app.get("/genai/explanations/{job_id}")
def read_genai_explanation(job_id: str):
    try:
        result = get_explanation_status(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(status_code=404, detail="GenAI job not found")

    return result


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/inventory/assess")
def assess_inventory(payload: InventoryRequest):
    inventory = Inventory(**payload.model_dump())
    result = inventory.assess_risk()
    probability = predict_stockout_probability(
        get_predictive_model(),
        stock=payload.stock,
        daily_usage=payload.daily_usage,
        safety_stock=payload.safety_stock,
        incoming_stock=payload.incoming_stock,
        delivery_delay_days=payload.delivery_delay_days,
    )
    result["predicted_stockout_probability_7_days"] = round(
        probability, 4
    )
    result["prediction_note"] = PREDICTION_NOTE

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "MANUAL_ASSESSMENT",
        "facility_id": payload.facility_id,
        "medicine": payload.medicine,
        "current_stock": payload.stock,
        "incoming_stock": payload.incoming_stock,
        "delivery_days_remaining": (
            payload.delivery_delay_days
            if payload.incoming_stock > 0
            else None
        ),
        "days_until_stockout": result["days_until_stockout"],
        "projected_days_until_stockout": (
            result["projected_days_until_stockout"]
        ),
        "risk": result["risk"],
        "predicted_stockout_probability_7_days": round(probability, 4),
        "prediction_note": PREDICTION_NOTE,
    }
    AuditLogger(AUDIT_LOG_PATH).record(event)

    return result


def read_audit_events() -> list[dict[str, Any]]:
    """Read valid JSON events, newest first."""
    if not AUDIT_LOG_PATH.is_file():
        return []

    events = []

    with AUDIT_LOG_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if isinstance(event, dict):
                events.append(event)

    events.reverse()
    return events


def filter_events(
    events: list[dict[str, Any]],
    facility_id: str | None,
    medicine: str | None,
) -> list[dict[str, Any]]:
    """Filter events by facility and medicine."""
    return [
        event
        for event in events
        if (facility_id is None or event.get("facility_id") == facility_id)
        and (medicine is None or event.get("medicine") == medicine)
    ]


@app.get("/events")
def get_events(
    limit: int = Query(default=50, ge=1, le=500),
    facility_id: str | None = None,
    medicine: str | None = None,
):
    events = filter_events(
        read_audit_events(), facility_id, medicine
    )
    events = events[:limit]

    return {"count": len(events), "events": events}


@app.get("/events/transitions")
def get_risk_transitions(
    limit: int = Query(default=50, ge=1, le=500),
    facility_id: str | None = None,
    medicine: str | None = None,
):
    events = [
        event
        for event in read_audit_events()
        if event.get("event_type") == "RISK_TRANSITION"
    ]

    events = filter_events(events, facility_id, medicine)
    events = events[:limit]

    return {"count": len(events), "events": events}



@app.get("/dashboard", include_in_schema=False)
def dashboard():
    dashboard_file = (
        Path(__file__).resolve().parent.parent
        / "static"
        / "dashboard.html"
    )
    return FileResponse(dashboard_file)
