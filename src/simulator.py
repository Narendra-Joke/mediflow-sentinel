import json
import random
import time
from datetime import datetime, timezone

from src.inventory import Inventory
from src.audit import AuditLogger


def make_event(tick, event_type, quantity, inventory, pending_delivery):
    """Capture an accurate inventory snapshot for one event."""
    if pending_delivery is None:
        inventory.incoming_stock = 0
        inventory.delivery_delay_days = 0
        delivery_days_remaining = None
    else:
        inventory.incoming_stock = pending_delivery["quantity"]
        inventory.delivery_delay_days = (
            pending_delivery["days_until_arrival"]
        )
        delivery_days_remaining = pending_delivery["days_until_arrival"]

    result = inventory.assess_risk()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "simulated_day": tick,
        "event_type": event_type,
        "facility_id": inventory.facility_id,
        "medicine": inventory.medicine,
        "quantity_changed": quantity,
        "current_stock": inventory.stock,
        "incoming_stock": inventory.incoming_stock,
        "delivery_days_remaining": delivery_days_remaining,
        "days_until_stockout": result["days_until_stockout"],
        "projected_days_until_stockout": (
            result["projected_days_until_stockout"]
        ),
        "risk": result["risk"],
    }


def main():
    random.seed(42)
    audit = AuditLogger()

    inventory = Inventory(
        facility_id="CLINIC-A",
        medicine="Amoxicillin",
        stock=60,
        daily_usage=15,
        safety_stock=30,
        incoming_stock=0,
        delivery_delay_days=0,
    )

    pending_delivery = None
    tick = 0

    print("MEDIFLOW SENTINEL - LIVE INVENTORY SIMULATOR")
    print("Each tick represents one simulated day.")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            tick += 1

            # Advance the pending shipment and receive it if due.
            if pending_delivery is not None:
                pending_delivery["days_until_arrival"] -= 1

                if pending_delivery["days_until_arrival"] <= 0:
                    received = pending_delivery["quantity"]
                    inventory.stock += received
                    pending_delivery = None

                    event = make_event(
                        tick,
                        "DELIVERY_RECEIVED",
                        received,
                        inventory,
                        pending_delivery,
                    )
                    audit.record(event)
                    print(json.dumps(event), flush=True)

            # Dispense medicine for this simulated day.
            quantity = min(
                inventory.stock,
                round(inventory.daily_usage),
            )
            inventory.stock -= quantity

            event_type = (
                "MEDICINE_DISPENSED"
                if quantity > 0
                else "NO_STOCK_AVAILABLE"
            )
            event = make_event(
                tick,
                event_type,
                quantity,
                inventory,
                pending_delivery,
            )
            audit.record(event)
            print(json.dumps(event), flush=True)

            # Schedule a new delivery only if no shipment is pending.
            if (
                pending_delivery is None
                and random.random() < 0.35
            ):
                pending_delivery = {
                    "quantity": random.randint(30, 60),
                    "days_until_arrival": random.randint(1, 3),
                }

                event = make_event(
                    tick,
                    "DELIVERY_SCHEDULED",
                    pending_delivery["quantity"],
                    inventory,
                    pending_delivery,
                )
                audit.record(event)
                print(json.dumps(event), flush=True)

            time.sleep(2)

    except KeyboardInterrupt:
        print("\nSimulator stopped.")


if __name__ == "__main__":
    main()
