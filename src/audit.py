import json
from pathlib import Path
from typing import Any


class AuditLogger:
    """Append simulator events to a persistent JSON Lines file."""

    def __init__(self, path: str = "data/audit_events.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: dict[str, Any]) -> None:
        """Append one event as a JSON object on its own line."""
        with self.path.open("a", encoding="utf-8") as file:
            file.write(
                json.dumps(event, separators=(",", ":")) + "\n"
            )

class RiskTransitionTracker:
    """Detect changes in risk for each facility and medicine."""

    def __init__(self):
        self._previous_risks = {}

    def observe(self, event: dict[str, Any]) -> dict[str, Any] | None:
        """Return a transition event when an existing risk changes."""
        key = (event["facility_id"], event["medicine"])
        current_risk = event["risk"]
        previous_risk = self._previous_risks.get(key)

        self._previous_risks[key] = current_risk

        if previous_risk is None or previous_risk == current_risk:
            return None

        return {
            "timestamp": event["timestamp"],
            "simulated_day": event["simulated_day"],
            "event_type": "RISK_TRANSITION",
            "facility_id": event["facility_id"],
            "medicine": event["medicine"],
            "previous_risk": previous_risk,
            "risk": current_risk,
            "current_stock": event["current_stock"],
            "days_until_stockout": event["days_until_stockout"],
            "projected_days_until_stockout": (
                event["projected_days_until_stockout"]
            ),
        }
