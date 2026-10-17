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
