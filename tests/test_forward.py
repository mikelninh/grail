import unittest

from grail.forward import update_forward_state
from grail.sales import SaleEvent


class ForwardLedgerTests(unittest.TestCase):
    def payload(self):
        return {
            "candidates": [
                {
                    "source_url": "https://example/c/alpha",
                    "collectible": "Alpha",
                    "mint": 1962,
                    "signal_class": "GRAIL",
                    "availability_status": "unconfirmed-live",
                    "listed_date": "2026-09-09",
                    "ask_usd": 100.0,
                    "ask_omi": 400000,
                    "floor_usd": 110.0,
                    "premium_to_floor_pct": -9.1,
                    "mint_score": 100.0,
                    "opportunity_score": 82.0,
                    "confidence": 88.0,
                    "stackr_url": "https://stackr.world/a",
                    "veve_url": "https://veve.me/a",
                },
                {
                    "source_url": "https://example/c/alpha",
                    "collectible": "Alpha",
                    "mint": 4321,
                    "signal_class": "MARKET",
                    "availability_status": "unconfirmed-live",
                    "listed_date": "2026-09-09",
                    "ask_usd": 80.0,
                    "ask_omi": 320000,
                    "floor_usd": 110.0,
                    "premium_to_floor_pct": -27.3,
                    "mint_score": 0.0,
                    "opportunity_score": 50.0,
                    "confidence": 80.0,
                },
                {
                    "source_url": "https://example/c/alpha",
                    "collectible": "Alpha",
                    "mint": 5555,
                    "signal_class": "EDGE",
                    "availability_status": "unconfirmed-live",
                    "listed_date": "2026-09-09",
                    "ask_usd": 85.0,
                    "ask_omi": 340000,
                    "floor_usd": 110.0,
                    "premium_to_floor_pct": -22.7,
                    "mint_score": 10.0,
                    "opportunity_score": 55.0,
                    "confidence": 80.0,
                },
            ]
        }

    def test_disappearance_does_not_fake_a_sale(self):
        first = update_forward_state(None, self.payload(), [], now="2026-09-09T00:00:00+00:00")
        second = update_forward_state(first, {"candidates": []}, [], now="2026-09-10T00:00:00+00:00")
        self.assertEqual(second["summary"]["resolved_sales"], 0)
        self.assertTrue(all(a["status"] == "open" for a in second["alerts"]))

    def test_matching_realised_sale_resolves_exact_mint(self):
        first = update_forward_state(None, self.payload(), [], now="2026-09-09T00:00:00+00:00")
        sale = SaleEvent(
            collectible_id="alpha",
            collectible="Alpha",
            mint=1962,
            marketplace="STACKR",
            price_usd=None,
            price_omi=500000,
            seller="@seller",
            buyer="@buyer",
            sold_date="2026-09-10",
            source_url="https://example/c/alpha",
            observed_at="2026-09-10T12:00:00+00:00",
        )
        second = update_forward_state(first, self.payload(), [sale], now="2026-09-10T12:00:00+00:00")
        alert = next(a for a in second["alerts"] if a["mint"] == 1962)
        self.assertEqual(alert["status"], "sold")
        self.assertEqual(alert["return_proxy_pct"], 25.0)
        other = next(a for a in second["alerts"] if a["mint"] == 5555)
        self.assertEqual(other["status"], "open")

    def test_freezes_baselines_at_first_alert(self):
        state = update_forward_state(None, self.payload(), [], now="2026-09-09T00:00:00+00:00")
        grail = next(a for a in state["alerts"] if a["mint"] == 1962)
        self.assertEqual(grail["baselines"]["cheapest"]["mint"], 4321)
        self.assertEqual(grail["baselines"]["deepest_discount"]["mint"], 4321)
        self.assertIn("control", grail["baselines"])


if __name__ == "__main__":
    unittest.main()
