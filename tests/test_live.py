import unittest

from grail.live import MarketObservation, parse_vevealpha_html, rank_observation


SAMPLE = """
<html><body>
<h1># Spider-Man – Jump into Action</h1>
<div>RARE COLLECTIBLE 8,999 editions</div>
<div>VeVe gem floor $59.50</div>
<div>StackR floor $28.34</div>
<div>Listings 30d 52</div>
</body></html>
"""


class LiveMarketTests(unittest.TestCase):
    def test_parse_server_rendered_market_page(self):
        obs = parse_vevealpha_html(SAMPLE, "https://example.test/spidey", "2026-09-08T00:00:00+00:00")
        self.assertEqual(obs.collectible, "Spider-Man – Jump into Action")
        self.assertEqual(obs.rarity, "RARE")
        self.assertEqual(obs.edition_size, 8999)
        self.assertEqual(obs.veve_floor_usd, 59.50)
        self.assertEqual(obs.stackr_floor_usd, 28.34)
        self.assertEqual(obs.listings_30d, 52)

    def test_gap_ranking_preserves_warning(self):
        obs = MarketObservation(
            source="VeVe Alpha",
            source_url="https://example.test",
            collectible="Spider-Man",
            rarity="COMMON",
            edition_size=14511,
            veve_floor_usd=13.20,
            stackr_floor_usd=5.90,
            listings_30d=30,
            observed_at="2026-09-08T00:00:00+00:00",
        )
        candidate = rank_observation(obs)
        self.assertEqual(candidate.cheaper_market, "StackR")
        self.assertAlmostEqual(candidate.nominal_gap_pct, 55.30, places=2)
        self.assertGreater(candidate.opportunity_score, 60)
        self.assertTrue(any("not executable arbitrage" in warning for warning in candidate.warnings))

    def test_low_activity_is_penalised_and_flagged(self):
        liquid = MarketObservation("x", "u", "liquid", None, 1000, 100, 50, 40, "t")
        thin = MarketObservation("x", "u", "thin", None, 1000, 100, 50, 1, "t")
        a = rank_observation(liquid)
        b = rank_observation(thin)
        self.assertGreater(a.opportunity_score, b.opportunity_score)
        self.assertTrue(any("very low" in warning for warning in b.warnings))


if __name__ == "__main__":
    unittest.main()
