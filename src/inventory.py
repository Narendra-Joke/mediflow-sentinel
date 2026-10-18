from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Inventory:
    facility_id: str
    medicine: str
    stock: int
    daily_usage: float
    safety_stock: int
    incoming_stock: int = 0
    delivery_delay_days: float = 0.0

    def assess_risk(self) -> dict:
        if self.stock < 0 or self.daily_usage < 0:
            raise ValueError("Stock and daily usage cannot be negative")

        if self.safety_stock < 0 or self.incoming_stock < 0:
            raise ValueError(
                "Safety stock and incoming stock cannot be negative"
            )

        if self.delivery_delay_days < 0:
            raise ValueError("Delivery delay cannot be negative")

        if self.daily_usage == 0:
            days_remaining = None
            projected_days = None
        else:
            days_remaining = self.stock / self.daily_usage

            # A shipment arriving too late cannot prevent stockout.
            if days_remaining <= self.delivery_delay_days:
                projected_days = days_remaining
            else:
                projected_days = (
                    self.stock + self.incoming_stock
                ) / self.daily_usage

        effective_days = (
            days_remaining
            if days_remaining is not None
            else float("inf")
        )

        if effective_days <= self.delivery_delay_days:
            risk = "CRITICAL"
            risk_reason = (
                "Current stock may run out before the delivery delay ends."
            )
            recommended_action = (
                "Urgently review expedited replenishment or alternative supply."
            )
        elif self.stock <= self.safety_stock:
            risk = "HIGH"
            risk_reason = (
                "Current stock is at or below the safety-stock threshold."
            )
            recommended_action = (
                "Review replenishment needs and confirm the delivery plan."
            )
        elif projected_days is not None and projected_days <= 3:
            risk = "HIGH"
            risk_reason = (
                "Projected stock coverage is 3 days or less."
            )
            recommended_action = (
                "Prioritize replenishment planning."
            )
        elif projected_days is not None and projected_days <= 7:
            risk = "MEDIUM"
            risk_reason = (
                "Projected stock coverage is 7 days or less."
            )
            recommended_action = (
                "Monitor stock and confirm the delivery schedule."
            )
        else:
            risk = "LOW"
            risk_reason = (
                "No higher-risk condition was triggered by the current rules."
            )
            recommended_action = (
                "Continue routine inventory monitoring."
            )

        return {
            **asdict(self),
            "days_until_stockout": (
                round(days_remaining, 2)
                if days_remaining is not None
                else None
            ),
            "projected_days_until_stockout": (
                round(projected_days, 2)
                if projected_days is not None
                else None
            ),
            "risk": risk,
            "risk_reason": risk_reason,
            "recommended_action": recommended_action,
            "assessed_at": datetime.now(timezone.utc).isoformat(),
        }


def main() -> None:
    facilities = [
        Inventory("CLINIC-A", "Amoxicillin", 20, 15, 30, 0, 2),
        Inventory("CLINIC-B", "Amoxicillin", 200, 20, 50, 0, 2),
        Inventory("CLINIC-C", "Amoxicillin", 100, 10, 30, 20, 3),
        Inventory("CLINIC-A", "Insulin", 12, 4, 10, 0, 2),
    ]

    print("MEDIFLOW SENTINEL - INVENTORY RISK REPORT")
    print("=" * 55)

    for item in facilities:
        result = item.assess_risk()
        days = result["days_until_stockout"]
        days_text = f"{days:.2f} days" if days is not None else "Unknown"

        print(
            f"{result['facility_id']:10} | "
            f"{result['medicine']:12} | "
            f"Stock: {result['stock']:4} | "
            f"Stockout: {days_text:12} | "
            f"Risk: {result['risk']}"
        )
        print(f"  Reason: {result['risk_reason']}")
        print(f"  Recommended action: {result['recommended_action']}")
        print("-" * 55)


if __name__ == "__main__":
    main()
