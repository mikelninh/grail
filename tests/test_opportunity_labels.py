import unittest

from api.opportunities import _signal_class


class OpportunityLabelTests(unittest.TestCase):
    def test_random_palindrome_is_not_a_grail(self):
        row = {
            "actionability": "verify-now",
            "mint_score": 38.0,
            "opportunity_score": 85.0,
            "premium_to_floor_pct": -55.0,
            "reasons": ("palindromic edition #2772", "current ask is 55% below daily StackR floor snapshot"),
        }
        self.assertEqual(_signal_class(row), "EDGE")

    def test_ip_significant_mint_can_be_grail(self):
        row = {
            "actionability": "verify-now",
            "mint_score": 100.0,
            "opportunity_score": 80.0,
            "premium_to_floor_pct": 5.0,
            "reasons": ("Spider-Man first appeared in Amazing Fantasy #15 in 1962",),
        }
        self.assertEqual(_signal_class(row), "GRAIL")

    def test_curated_low_mint_can_be_grail(self):
        row = {
            "actionability": "verify-now",
            "mint_score": 94.0,
            "opportunity_score": 70.0,
            "premium_to_floor_pct": 10.0,
            "reasons": ("low edition #41",),
            "discovery_source": "curated",
        }
        self.assertEqual(_signal_class(row), "GRAIL")

    def test_universe_generic_low_mint_is_not_automatically_grail(self):
        row = {
            "actionability": "verify-now",
            "mint_score": 94.0,
            "opportunity_score": 70.0,
            "premium_to_floor_pct": 10.0,
            "reasons": ("low edition #41",),
            "discovery_source": "universe",
            "provider_grail": False,
            "provider_alpha": False,
            "catalog_is_fa": False,
        }
        self.assertEqual(_signal_class(row), "WATCH")

    def test_universe_provider_grail_needs_exceptional_mint(self):
        base = {
            "actionability": "verify-now",
            "opportunity_score": 75.0,
            "premium_to_floor_pct": 5.0,
            "reasons": ("low edition #41",),
            "discovery_source": "universe",
            "provider_grail": True,
            "provider_alpha": True,
            "catalog_is_fa": True,
        }
        self.assertEqual(_signal_class({**base, "mint_score": 70.0}), "WATCH")
        self.assertEqual(_signal_class({**base, "mint_score": 88.0}), "GRAIL")

    def test_universe_strong_ip_semantic_can_be_grail(self):
        row = {
            "actionability": "verify-now",
            "mint_score": 90.0,
            "opportunity_score": 72.0,
            "premium_to_floor_pct": 2.0,
            "reasons": ("Order 66 is a defining Star Wars reference",),
            "discovery_source": "universe",
            "provider_grail": False,
        }
        self.assertEqual(_signal_class(row), "GRAIL")


if __name__ == "__main__":
    unittest.main()
