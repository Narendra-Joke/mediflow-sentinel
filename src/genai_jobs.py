import json
import os
import re
from pathlib import Path
from uuid import uuid4
from typing import Any

JOB_DIR = Path(
    os.environ.get(
        "MEDIFLOW_GENAI_JOB_DIR",
        "/home/linux1/shared/mediflow-jobs",
    )
)

JOB_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")


def _job_path(prefix: str, job_id: str) -> Path:
    if not JOB_ID_PATTERN.fullmatch(job_id):
        raise ValueError("Invalid job ID")
    return JOB_DIR / f"{prefix}_{job_id}.json"


def submit_explanation(assessment: dict[str, Any]) -> str:
    """Atomically queue an assessment for the GenAI worker."""
    JOB_DIR.mkdir(parents=True, exist_ok=True)
    job_id = uuid4().hex
    destination = _job_path("request", job_id)
    temporary = JOB_DIR / f".request_{job_id}.tmp"

    try:
        temporary.write_text(
            json.dumps(
                {"job_id": job_id, "assessment": assessment},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)

    return job_id


def get_explanation_status(job_id: str) -> dict[str, Any] | None:
    """Return the result, pending state, or None for an unknown job."""
    result_path = _job_path("result", job_id)

    if result_path.is_file():
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"job_id": job_id, "status": "pending"}

        if isinstance(result, dict) and result.get("job_id") == job_id:
            return result

        return {"job_id": job_id, "status": "pending"}

    request_path = _job_path("request", job_id)
    processing_path = _job_path("processing", job_id)

    if request_path.exists() or processing_path.exists():
        return {"job_id": job_id, "status": "pending"}

    return None
