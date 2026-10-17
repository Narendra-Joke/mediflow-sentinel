
from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator

from src.inventory import Inventory

app = FastAPI(
    title="Mediflow Sentinel API",
    description="Medicine inventory risk assessment service",
    version="1.0.0",
)

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
