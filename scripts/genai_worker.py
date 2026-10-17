import json
import os
import time
import traceback
from pathlib import Path

from llama_cpp import Llama

SHARED = Path("/home/ibm-user/shared/mediflow-jobs")
MODEL = Path(
    "/home/ibm-user/shared/models/"
    "granite-3.3-2b-instruct-Q4_K_M.gguf"
)
POLL_SECONDS = 2
MAX_TOKENS = 120

def atomic_json_write(path: Path, data: dict) -> None:
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(temp, path)

def main() -> None:
    SHARED.mkdir(parents=True, exist_ok=True)

    if not MODEL.is_file():
        raise FileNotFoundError(f"Model not found: {MODEL}")

    print("Loading Granite model; this may take a little while...", flush=True)
    model = Llama(
        model_path=str(MODEL),
        n_ctx=1024,
        n_threads=3,
        verbose=False,
    )
    print("Mediflow GenAI worker is ready.", flush=True)

    while True:
        requests = sorted(SHARED.glob("request_*.json"))

        if not requests:
            time.sleep(POLL_SECONDS)
            continue

        request_path = requests[0]
        job_id = request_path.stem.removeprefix("request_")
        processing_path = SHARED / f"processing_{job_id}.json"
        result_path = SHARED / f"result_{job_id}.json"

        try:
            os.replace(request_path, processing_path)
        except FileNotFoundError:
            continue

        started = time.time()

        try:
            job = json.loads(processing_path.read_text(encoding="utf-8"))
            assessment = job.get("assessment", {})

            if not isinstance(assessment, dict):
                raise ValueError("Assessment must be a JSON object")

            prompt_data = json.dumps(assessment, ensure_ascii=False)

            response = model.create_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Mediflow Sentinel, an assistant that "
                            "explains medicine inventory risk assessments. "
                            "Use only the supplied assessment data. "
                            "Explain the risk, key contributing factors, "
                            "and practical inventory follow-up actions. "
                            "Do not diagnose patients, recommend patient "
                            "treatment, invent facts, or claim that an "
                            "experimental prediction is clinically validated. "
                            "If information is missing, say so. Be concise."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "Explain this inventory assessment in plain "
                            "language:\n" + prompt_data
                        ),
                    },
                ],
                max_tokens=MAX_TOKENS,
                temperature=0.2,
            )

            answer = response["choices"][0]["message"]["content"].strip()
            atomic_json_write(
                result_path,
                {
                    "job_id": job_id,
                    "status": "completed",
                    "answer": answer,
                    "model": "Granite 3.3 2B Instruct",
                    "experimental": True,
                    "duration_seconds": round(time.time() - started, 2),
                },
            )
            print(f"Completed job {job_id}", flush=True)

        except Exception as exc:
            atomic_json_write(
                result_path,
                {
                    "job_id": job_id,
                    "status": "failed",
                    "error": str(exc),
                },
            )
            print(f"Job {job_id} failed: {exc}", flush=True)

        finally:
            processing_path.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
