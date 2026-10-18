import json
import os
import re
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
                            "You are Mediflow Sentinel. Explain the supplied "
                            "inventory assessment using only its exact values. "
                            "Never calculate, guess, or change any number, "
                            "probability, risk level, or stockout timeline. "
                            "If a value is missing, do not invent it. "
                            "Write exactly 3 short sentences: (1) stock and "
                            "estimated days until stockout, (2) supplied risk "
                            "level and probability, if present, (3) one practical "
                            "inventory action consistent with the assessment. "
                            "End by stating predictions are experimental and "
                            "not clinically validated. Do not diagnose patients "
                            "or recommend treatment. Keep under 80 words."
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

            # Keep structured assessment values authoritative.
            def fmt(value):
                if isinstance(value, float) and value.is_integer():
                    return str(int(value))
                return str(value)

            stock = assessment.get("stock")
            usage = assessment.get("daily_usage")
            days = assessment.get(
                "projected_days_until_stockout",
                assessment.get("days_until_stockout"),
            )
            risk = assessment.get("risk")
            probability = assessment.get("predicted_stockout_probability_7_days")
            action = assessment.get("recommended_action")
            facility = assessment.get("facility_id", "the facility")
            medicine = assessment.get("medicine", "medicine")

            probability_text = (
                f"{probability * 100:.2f}%"
                if isinstance(probability, (int, float))
                else None
            )

            # Normalize decimal probability to a human-readable percentage.
            if probability_text:
                raw_probability = fmt(probability)
                answer = re.sub(
                    rf"\b{re.escape(raw_probability)}\s*"
                    rf"\(\s*{re.escape(probability_text)}\s*\)",
                    probability_text,
                    answer,
                )
                answer = re.sub(
                    rf"\b{re.escape(raw_probability)}\b",
                    probability_text,
                    answer,
                )

            # Reject contradictory numbers or missing required facts.
            allowed_numbers = {
                float(value)
                for value in assessment.values()
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            }
            allowed_numbers.add(7.0)

            found_numbers = re.findall(
                r"(?<![A-Za-z])\d+(?:\.\d+)?%?", answer
            )
            numbers_valid = all(
                float(token.rstrip("%")) in allowed_numbers
                or (
                    probability_text is not None
                    and token == probability_text
                )
                for token in found_numbers
            )

            sentence_count = len(
                re.split(r"(?<=[.!?])\s+", answer.strip())
            )
            required_facts = [
                fmt(stock) if stock is not None else None,
                fmt(usage) if usage is not None else None,
                fmt(days) if days is not None else None,
                str(risk) if risk is not None else None,
                probability_text,
                str(action).rstrip(".") if action else None,
                "not clinically validated",
            ]
            facts_valid = all(
                fact is None or fact.lower() in answer.lower()
                for fact in required_facts
            )

            if not numbers_valid or not facts_valid or sentence_count != 3:
                # Safe deterministic fallback: never let the model alter facts.
                sentence1 = (
                    f"{medicine} at {facility} has {fmt(stock)} units in stock"
                    f" and daily usage is {fmt(usage)} units, with an estimated"
                    f" {fmt(days)} days until stockout."
                )
                sentence2 = (
                    f"Risk is {risk}"
                    + (
                        f", with a {probability_text} probability of stockout "
                        "within 7 days."
                        if probability_text
                        else "."
                    )
                )
                sentence3 = (
                    f"Recommended action: {str(action).rstrip('.')} "
                    "Predictions are experimental and not clinically validated."
                )
                # Keep the action and disclaimer in one sentence.
                sentence3 = (
                    f"Recommended action: {str(action).rstrip('.').lower()}; "
                    "predictions are experimental and not clinically validated."
                )
                answer = f"{sentence1} {sentence2} {sentence3}"
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
