
# Mediflow Sentinel

A medicine inventory risk assessment API built with Python and FastAPI.

## Features

- Assess medicine inventory risk.
- Calculate estimated days until stockout.
- Classify inventory as CRITICAL, HIGH, MEDIUM, or LOW risk.
- Validate inventory inputs using Pydantic.
- Provide a health-check endpoint.
- Include automated API and inventory tests.

## Requirements

- Python 3.12+
- pip

## Setup

Clone the repository and enter the project directory:

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd mediflow-sentinel
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the API

```bash
uvicorn src.api:app --host 127.0.0.1 --port 8000
```

Open the interactive API documentation:

http://127.0.0.1:8000/docs

## API Endpoints

### Health check

`GET /health`

Example response:

```json
{
  "status": "healthy"
}
```

### Assess inventory risk

`POST /inventory/assess`

Example request:

```json
{
  "facility_id": "CLINIC-A",
  "medicine": "Amoxicillin",
  "stock": 20,
  "daily_usage": 15,
  "safety_stock": 30,
  "incoming_stock": 0,
  "delivery_delay_days": 2
}
```

The response includes the inventory details, estimated
days until stockout, risk classification, and assessment timestamp.

## Run tests

```bash
python -m pytest -v
```

## Project Structure

```text
mediflow-sentinel/
├── src/
│   ├── api.py
│   ├── inventory.py
│   └── simulator.py
├── tests/
│   ├── test_api.py
│   └── test_inventory.py
├── requirements.txt
├── .gitignore
└── README.md
```

## License

Add a license before distributing the project publicly.
