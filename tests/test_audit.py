import json

from src.audit import AuditLogger


def test_record_appends_event_as_json_line(tmp_path):
    path = tmp_path / "audit_events.jsonl"
    logger = AuditLogger(str(path))

    event = {
        "event_type": "MEDICINE_DISPENSED",
        "facility_id": "CLINIC-A",
        "medicine": "Amoxicillin",
        "current_stock": 45,
        "risk": "MEDIUM",
    }

    logger.record(event)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == event


def test_record_preserves_previous_events(tmp_path):
    path = tmp_path / "audit_events.jsonl"
    logger = AuditLogger(str(path))

    first = {"event_type": "MEDICINE_DISPENSED", "current_stock": 45}
    second = {"event_type": "DELIVERY_SCHEDULED", "incoming_stock": 40}

    logger.record(first)
    logger.record(second)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == first
    assert json.loads(lines[1]) == second

