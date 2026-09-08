import unittest

from grail.live import MarketObservation
from grail.mint_live import EditionListing, parse_latest_stackr_listings, score_mint_listing
from grail.models import Collectible


HTML = """
<html><body>
<h3>Latest listings</h3>
<div>15 Aug · #443 VEVE —</div>
<div>14 Aug · #967 STACKR 64,999 OMI · ≈ $12.30</div>
<div>14 Aug · #1038 STACKR 65,000 OMI · ≈ $12.30</div>
<div>7 Aug · #237 STACKR 229,000 OMI · ≈ $43.33</div>
<h3>Recent sales</h3>
<div>14 Aug · #967 VeVe $14.00</div>
</body></html>
"""

OMI_USD = 0.0002323


class MintLiveTests(unittest.TestCase):
    def test_parse_stackr_edition_listings_with_age(self):
        rows = parse_latest_stackr_listings(HTML, "Excelsior!", "https://example.test", "2026-08-15T12:00:00+00:00")
        self.assertEqual([r.mint for r in rows], [967, 1038, 237])
        self.assertEqual(rows[0].ask_omi, 64999)
        self.assertEqual(rows[0].ask_usd, 12.30)
        self.assertEqual(rows[0].listed_date, "2026-08-14")
        self.assertEqual(rows[0].age_days, 1)
        self.assertEqual(rows[2].age_days, 8)

    def test_semantic_mint_can_beat_plain_floor_position(self):
        market = MarketObservation("x", "u", "Spider-Man", "COMMON", 10000, 100.0, 100.0, 20, "2026-09-08T00:00:00+00:00")
        collectible = Collectible(
            id="spidey",
            name="Spider-Man",
            brand="Marvel",
            character="Spider-Man",
            total_editions=10000,
            first_appearance_year=1962,
            semantic_numbers=(1962,),
            semantic_labels={1962: "Spider-Man first appeared in 1962"},
        )
        semantic = score_mint_listing(EditionListing("Spider-Man", 1962, "StackR", 70.0, 465000, "u", "t", "2026-08-14", 25), market, collectible, OMI_USD)
        plain = score_mint_listing(EditionListing("Spider-Man", 4321, "StackR", 70.0, 387000, "u", "t", "2026-08-14", 25), market, collectible, OMI_USD)
        self.assertGreater(semantic.opportunity_score, plain.opportunity_score)
        self.assertGreaterEqual(semantic.mint_score, 90)
        self.assertEqual(semantic.actionability, "verify-now")

    def test_extreme_premium_is_hard_capped(self):
        market = MarketObservation("x", "u", "Spider-Man", "COMMON", 10000, 100.0, 100.0, 20, "t")
        collectible = Collectible("spidey", "Spider-Man", "Marvel", "Spider-Man", total_editions=10000, semantic_numbers=(1962,), semantic_labels={1962:"debut year"})
        sane = score_mint_listing(EditionListing("Spider-Man", 1962, "StackR", 50.0, 473000, "u", "t"), market, collectible, OMI_USD)
        absurd = score_mint_listing(EditionListing("Spider-Man", 1962, "StackR", 50.0, 1722000, "u", "t"), market, collectible, OMI_USD)
        self.assertGreater(sane.opportunity_score, absurd.opportunity_score)
        self.assertLessEqual(absurd.opportunity_score, 20)
        self.assertEqual(absurd.actionability, "reject-price")

    def test_old_usd_label_is_repriced_with_current_omi(self):
        market = MarketObservation("x", "u", "Goofy", "COMMON", 10000, 6.61, 6.61, 20, "t")
        collectible = Collectible("goofy", "Goofy", "Disney", "Goofy", total_editions=10000)
        row = EditionListing("Goofy", 323, "StackR", 1.65, 64999, "u", "t", "2026-09-04", 4)
        candidate = score_mint_listing(row, market, collectible, OMI_USD)
        self.assertAlmostEqual(candidate.ask_usd, 15.10, places=2)
        self.assertGreater(candidate.premium_to_floor_pct, 100)
        self.assertEqual(candidate.actionability, "reject-price")

    def test_missing_current_omi_rate_cannot_be_actionable(self):
        market = MarketObservation("x", "u", "Spider-Man", "COMMON", 10000, 100.0, 100.0, 20, "t")
        collectible = Collectible("spidey", "Spider-Man", "Marvel", "Spider-Man", total_editions=10000)
        candidate = score_mint_listing(EditionListing("Spider-Man", 100, "StackR", 50.0, 200000, "u", "t"), market, collectible, None)
        self.assertEqual(candidate.actionability, "pricing-unverified")
        self.assertLessEqual(candidate.opportunity_score, 35)


if __name__ == "__main__":
    unittest.main()
