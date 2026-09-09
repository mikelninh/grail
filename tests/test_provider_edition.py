import unittest
from unittest.mock import patch

from grail.provider_edition import PublicSupabaseConfig, lookup_edition


class ProviderEditionTests(unittest.TestCase):
    def test_onchain_owner_is_normalized_without_inventing_token_id(self):
        raw = {
            "name": "Example Collectible",
            "edition": 851,
            "seen": True,
            "onchain_found": True,
            "onchain_owner": "0x9b56281436e7488dde4d0102056cb607d4749e47",
            "onchain_coverage_pct": 83.5,
        }
        with patch("grail.provider_edition.discover_public_supabase_config", return_value=PublicSupabaseConfig("https://example.supabase.co", "anon")), \
             patch("grail.provider_edition.extract_collectible_id", return_value="96efdc03-c20e-4816-9644-248821fcbb9a"), \
             patch("grail.provider_edition._rpc", return_value=raw):
            result = lookup_edition("https://vevealpha.com/c/example", 851)
        self.assertEqual(result.edition, 851)
        self.assertEqual(result.owner, "0x9b56281436e7488dde4d0102056cb607d4749e47")
        self.assertIsNone(result.token_id)

    def test_wrong_edition_fails_closed(self):
        with patch("grail.provider_edition.discover_public_supabase_config", return_value=PublicSupabaseConfig("https://example.supabase.co", "anon")), \
             patch("grail.provider_edition.extract_collectible_id", return_value="96efdc03-c20e-4816-9644-248821fcbb9a"), \
             patch("grail.provider_edition._rpc", return_value={"edition": 852, "onchain_owner": "0x9b56281436e7488dde4d0102056cb607d4749e47"}):
            with self.assertRaises(ValueError):
                lookup_edition("https://vevealpha.com/c/example", 851)


if __name__ == "__main__":
    unittest.main()
