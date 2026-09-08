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


class MintLiveTests(unittest.TestCase):
    def test_parse_stackr_edition_listings_with_freshness(self):
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
        semantic = score_mint_listing(EditionListing("Spider-Man", 1962, "StackR", 108.0, 1, "u", "2026-09-08T00:00:00+00:00", "2026-09-08", 0), market, collectible)
        plain = score_mint_listing(EditionListing("Spider-Man", 4321, "StackR", 90.0, 1, "u", "2026-09-08T00:00:00+00:00", "2026-09-08", 0), market, collectible)
        self.assertGreater(semantic.opportunity_score, plain.opportunity_score)
        self.assertGreaterEqual(semantic.mint_score, 90)
        self.assertEqual(semantic.actionability, "verify-now")

    def test_extreme_premium_is_hard_capped(self):
        market = MarketObservation("x", "u", "Spider-Man", "COMMON", 10000, 100.0, 100.0, 20, "2026-09-08T00:00:00+00:00")
        collectible = Collectible("spidey", "Spider-Man", "Marvel", "Spider-Man", total_editions=10000, semantic_numbers=(1962,), semantic_labels={1962:"debut year"})
        sane = score_mint_listing(EditionListing("Spider-Man", 1962, "StackR", 110.0, 1, "u", "2026-09-08T00:00:00+00:00", "2026-09-08", 0), market, collectible)
        absurd = score_mint_listing(EditionListing("Spider-Man", 1962, "StackR", 400.0, 1, "u", "2026-09-08T00:00:00+00:00", "2026-09-08", 0), market, collectible)
        self.assertGreater(sane.opportunity_score, absurd.opportunity_score)
        self.assertLessEqual(absurd.opportunity_score, 20)
        self.assertTrue(any("above current StackR floor" in reason for reason in absurd.reasons))

    def test_stale_listing_event_cannot_rank_as_actionable_snipe(self):
        market = MarketObservation("x", "u", "Spider-Man", "COMMON", 10000, 100.0, 100.0, 20, "2026-09-08T00:00:00+00:00")
        collectible = Collectible("spidey", "Spider-Man", "Marvel", "Spider-Man", total_editions=10000, semantic_numbers=(1962,), semantic_labels={1962:"debut year"})
        stale = score_mint_listing(EditionListing("Spider-Man", 1962, "StackR", 50.0, 1, "u", "2026-09-08T00:00:00+00:00", "2026-08-14", 25), market, collectible)
        self.assertEqual(stale.actionability, "historical-signal")
        self.assertLessEqual(stale.opportunity_score, 45)


if __name__ == "__main__":
    unittest.main()
