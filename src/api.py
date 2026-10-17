import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field, field_validator

from src.inventory import Inventory

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


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/inventory/assess")
def assess_inventory(payload: InventoryRequest):
    inventory = Inventory(**payload.model_dump())
    return inventory.assess_risk()


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
