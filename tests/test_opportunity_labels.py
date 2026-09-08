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

    def test_low_mint_can_be_grail(self):
        row = {
            "actionability": "verify-now",
            "mint_score": 94.0,
            "opportunity_score": 70.0,
            "premium_to_floor_pct": 10.0,
            "reasons": ("low edition #41",),
        }
        self.assertEqual(_signal_class(row), "GRAIL")


if __name__ == "__main__":
    unittest.main()
