import json
import random
import time
from datetime import datetime, timezone

from src.inventory import Inventory


def main():
    random.seed(42)

    inventory = Inventory(
        facility_id="CLINIC-A",
        medicine="Amoxicillin",
        stock=60,
        daily_usage=15,
        safety_stock=30,
        incoming_stock=0,
        delivery_delay_days=2,
    )

    print("MEDIFLOW SENTINEL - LIVE INVENTORY SIMULATOR")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            # Simulate medicine consumption or an incoming delivery.
            if random.random() < 0.15:
                quantity = random.randint(10, 30)
                inventory.stock += quantity
                event_type = "DELIVERY_RECEIVED"
            else:
                quantity = min(
                    inventory.stock,
                    random.randint(1, 8),
                )
                inventory.stock -= quantity
                event_type = "MEDICINE_DISPENSED"

            result = inventory.assess_risk()

            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                "facility_id": inventory.facility_id,
                "medicine": inventory.medicine,
                "quantity_changed": quantity,
                "current_stock": inventory.stock,
                "days_until_stockout": result["days_until_stockout"],
                "risk": result["risk"],
            }

            print(json.dumps(event), flush=True)
            time.sleep(2)

    except KeyboardInterrupt:
        print("\nSimulator stopped.")


if __name__ == "__main__":
    main()
