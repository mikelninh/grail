import unittest
from grail.models import Collectible, Listing
from grail.scoring import score_listing


class ScoringTests(unittest.TestCase):
    def test_semantic_mint_can_beat_plain_floor_when_premium_is_small(self):
        c = Collectible("x", "Spider-Man", "Marvel", total_editions=10000, first_appearance_year=1962, semantic_numbers=(1962,))
        common = dict(collectible_id="x", marketplace="StackR", market_floor_usd=100, recent_sales_usd=(95,100,105), sales_30d=20, active_listings=12)
        self.assertGreater(score_listing(Listing("semantic", mint=1962, ask_usd=106, **common), c).total, score_listing(Listing("floor", mint=4273, ask_usd=100, **common), c).total)

    def test_huge_overpay_not_rescued_by_mint(self):
        c = Collectible("x", "Spider-Man", "Marvel", total_editions=10000, first_appearance_year=1962, semantic_numbers=(1962,))
        listing = Listing("bad", "x", "StackR", 1962, 300, 100, (95,100,105), 20, 12)
        self.assertLess(score_listing(listing, c).total, 60)


if __name__ == "__main__": unittest.main()
