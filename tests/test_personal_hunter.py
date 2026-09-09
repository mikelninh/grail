import unittest

from grail.personal_hunter import HunterPreferences, candidate_key, rank_personal, score_personal


def row(**overrides):
    base = {
        "source_url": "https://vevealpha.com/c/example",
        "mint": 66,
        "live_status": "live",
        "signal_class": "GRAIL",
        "actionability": "verify-now",
        "opportunity_score": 70,
        "ask_usd": 100,
        "premium_to_floor_pct": -10,
        "category": "Star Wars",
        "collectible": "Darth Vader",
        "reasons": ["Order 66 identity number"],
    }
    base.update(overrides)
    return base


class PersonalHunterTests(unittest.TestCase):
    def test_budget_filters_expensive_candidate(self):
        prefs = HunterPreferences(budget_usd=50)
        score, why = score_personal(row(ask_usd=100), prefs)
        self.assertLess(score, -1000)
        self.assertIn("over budget", why)

    def test_owned_candidate_is_excluded(self):
        r = row()
        prefs = HunterPreferences(owned_keys={candidate_key(r)})
        score, why = score_personal(r, prefs)
        self.assertLess(score, -1000)
        self.assertIn("already owned", why)

    def test_preferences_raise_matching_candidate(self):
        prefs = HunterPreferences(categories={"Star Wars"}, mint_preferences={"ip"})
        score, why = score_personal(row(), prefs)
        self.assertGreater(score, 90)
        self.assertTrue(any("Star Wars" in x for x in why))
        self.assertTrue(any("ip" in x for x in why))

    def test_watchlist_candidate_gets_priority(self):
        watched = row(source_url="https://vevealpha.com/c/watched", collectible="Yoda", mint=41, opportunity_score=61)
        plain = row(source_url="https://vevealpha.com/c/plain", collectible="Vader", mint=66, opportunity_score=70)
        prefs = HunterPreferences(watch_keys={candidate_key(watched)})
        picks = rank_personal([plain, watched], prefs, limit=2)
        self.assertEqual(picks[0]["collectible"], "Yoda")
        self.assertIn("on your watchlist", picks[0]["personal_why"])

    def test_friend_owner_hint_is_detected_and_penalised(self):
        prefs = HunterPreferences(friend_owner_hints={"Dorian": "0x67...9938"})
        score1, why1 = score_personal(row(current_owner="0x67abcdef9938"), prefs)
        score2, _ = score_personal(row(current_owner="0x9912340000"), prefs)
        self.assertLess(score1, score2)
        self.assertTrue(any("Dorian" in x for x in why1))

    def test_unicode_wallet_ellipsis_supported(self):
        prefs = HunterPreferences(friend_owner_hints={"Dorian": "0x67…9938"})
        score, why = score_personal(row(owner="0x67abcdef9938"), prefs)
        self.assertTrue(any("Dorian" in x for x in why))
        self.assertGreater(score, 0)

    def test_rank_deduplicates_collectible(self):
        rows = [row(mint=66), row(mint=501, opportunity_score=69), row(source_url="https://vevealpha.com/c/other", collectible="Yoda", mint=41)]
        picks = rank_personal(rows, HunterPreferences(), limit=3)
        self.assertEqual(len(picks), 2)
        self.assertEqual(len({p["source_url"] for p in picks}), 2)


if __name__ == "__main__":
    unittest.main()
