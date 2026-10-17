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


