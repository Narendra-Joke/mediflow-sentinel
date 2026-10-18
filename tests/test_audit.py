import json

from src.audit import AuditLogger
from src.audit import RiskTransitionTracker

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

def make_risk_event(risk, facility_id="CLINIC-A",
                    medicine="Amoxicillin"):
    return {
        "timestamp": "2026-10-17T08:00:00+00:00",
        "simulated_day": 1,
        "event_type": "MEDICINE_DISPENSED",
        "facility_id": facility_id,
        "medicine": medicine,
        "current_stock": 30,
        "days_until_stockout": 2.0,
        "projected_days_until_stockout": 2.0,
        "risk": risk,
    }


def test_first_risk_establishes_baseline():
    tracker = RiskTransitionTracker()

    result = tracker.observe(make_risk_event("LOW"))

    assert result is None


def test_same_risk_does_not_create_transition():
    tracker = RiskTransitionTracker()
    tracker.observe(make_risk_event("HIGH"))

    result = tracker.observe(make_risk_event("HIGH"))

    assert result is None


def test_risk_change_creates_transition_event():
    tracker = RiskTransitionTracker()
    tracker.observe(make_risk_event("MEDIUM"))

    result = tracker.observe(make_risk_event("HIGH"))

    assert result is not None
    assert result["event_type"] == "RISK_TRANSITION"
    assert result["previous_risk"] == "MEDIUM"
    assert result["risk"] == "HIGH"
    assert result["facility_id"] == "CLINIC-A"
    assert result["medicine"] == "Amoxicillin"


def test_risks_are_tracked_separately_per_medicine():
    tracker = RiskTransitionTracker()
    tracker.observe(make_risk_event("LOW", medicine="Amoxicillin"))

    result = tracker.observe(make_risk_event("HIGH", medicine="Paracetamol"))

    assert result is None


def test_record_event_persists_risk_transition(tmp_path, capsys):
    from src.simulator import record_event

    audit = AuditLogger(tmp_path / "events.jsonl")
    tracker = RiskTransitionTracker()

    record_event(make_risk_event("HIGH"), audit, tracker)
    record_event(make_risk_event("MEDIUM"), audit, tracker)

    lines = (tmp_path / "events.jsonl").read_text().splitlines()
    events = [json.loads(line) for line in lines]

    assert len(events) == 3
    assert events[0]["risk"] == "HIGH"
    assert events[1]["risk"] == "MEDIUM"
    assert events[2]["event_type"] == "RISK_TRANSITION"
    assert events[2]["previous_risk"] == "HIGH"
    assert events[2]["risk"] == "MEDIUM"

    output_lines = capsys.readouterr().out.splitlines()
    assert len(output_lines) == 3
    assert json.loads(output_lines[2])["event_type"] == "RISK_TRANSITION"
