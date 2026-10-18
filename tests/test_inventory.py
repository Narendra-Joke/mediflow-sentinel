import unittest

from src.inventory import Inventory


class TestInventoryRisk(unittest.TestCase):

    def test_critical_risk(self):
        item = Inventory("TEST-A", "Medicine-A", 20, 15, 30, 0, 2)
        self.assertEqual(item.assess_risk()["risk"], "CRITICAL")

    def test_high_risk(self):
        item = Inventory("TEST-B", "Medicine-B", 12, 4, 10, 0, 2)
        self.assertEqual(item.assess_risk()["risk"], "HIGH")

    def test_medium_risk(self):
        item = Inventory("TEST-D", "Medicine-D", 80, 20, 10, 0, 1)
        self.assertEqual(item.assess_risk()["risk"], "MEDIUM")

    def test_low_risk(self):
        item = Inventory("TEST-C", "Medicine-C", 200, 20, 50, 0, 2)
        self.assertEqual(item.assess_risk()["risk"], "LOW")

    def test_zero_usage(self):
        item = Inventory("TEST-E", "Medicine-E", 100, 0, 10, 0, 2)
        result = item.assess_risk()

        self.assertEqual(result["risk"], "LOW")
        self.assertIsNone(result["days_until_stockout"])

    def test_negative_stock_is_rejected(self):
        item = Inventory("TEST-F", "Medicine-F", -1, 10, 5, 0, 2)

        with self.assertRaises(ValueError):
            item.assess_risk()


if __name__ == "__main__":
    unittest.main()


def test_on_time_incoming_stock_reduces_risk():
    item = Inventory(
        "TEST-G", "Medicine-G",
        stock=20,
        daily_usage=10,
        safety_stock=5,
        incoming_stock=100,
        delivery_delay_days=1,
    )

    result = item.assess_risk()

    assert result["risk"] == "LOW"
    assert result["days_until_stockout"] == 2.0


def test_late_incoming_stock_does_not_hide_critical_risk():
    item = Inventory(
        "TEST-H", "Medicine-H",
        stock=10,
        daily_usage=10,
        safety_stock=2,
        incoming_stock=100,
        delivery_delay_days=2,
    )

    result = item.assess_risk()

    assert result["risk"] == "CRITICAL"
    assert result["days_until_stockout"] == 1.0


def test_critical_risk_has_explanation_and_action():
    item = Inventory("CLINIC-A", "Amoxicillin", 10, 10, 2, 100, 2)

    result = item.assess_risk()

    assert result["risk"] == "CRITICAL"
    assert "before the delivery delay ends" in result["risk_reason"]
    assert "Urgently review" in result["recommended_action"]


def test_safety_stock_high_risk_has_explanation():
    item = Inventory("CLINIC-A", "Amoxicillin", 5, 1, 10)

    result = item.assess_risk()

    assert result["risk"] == "HIGH"
    assert "safety-stock threshold" in result["risk_reason"]
    assert result["recommended_action"]


def test_projected_high_risk_has_explanation():
    item = Inventory("CLINIC-A", "Amoxicillin", 40, 20, 10)

    result = item.assess_risk()

    assert result["risk"] == "HIGH"
    assert "3 days or less" in result["risk_reason"]
    assert result["recommended_action"]


def test_medium_risk_has_explanation():
    item = Inventory("CLINIC-A", "Amoxicillin", 50, 10, 5)

    result = item.assess_risk()

    assert result["risk"] == "MEDIUM"
    assert "7 days or less" in result["risk_reason"]
    assert result["recommended_action"]


def test_low_risk_has_explanation():
    item = Inventory("CLINIC-A", "Amoxicillin", 100, 10, 5)

    result = item.assess_risk()

    assert result["risk"] == "LOW"
    assert result["risk_reason"]
    assert result["recommended_action"]
