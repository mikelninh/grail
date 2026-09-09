import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from grail.ownership import TokenMapping, load_mappings, resolve_mapping


class OwnershipResolverTests(unittest.TestCase):
    def test_registry_rejects_invalid_contract(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "mappings.json"
            p.write_text(json.dumps({"mappings": [{
                "source_url": "https://example/c/x",
                "mint": 777,
                "contract": "not-a-contract",
                "token_id": "123",
                "evidence_url": "https://collectscan.com/token/x",
                "mapping_method": "manual-exact",
            }]}))
            with self.assertRaises(ValueError):
                load_mappings(p)

    @patch("grail.ownership._get_json")
    def test_exact_mapping_resolves_owner_and_transfers(self, get_json):
        get_json.side_effect = [
            {
                "metadata": {"name": "Spider-Man"},
                "owner": {"hash": "0x1111111111111111111111111111111111111111"},
            },
            {"items": [{"transaction_hash": "0xabc"}]},
        ]
        mapping = TokenMapping(
            source_url="https://example/c/spider-man",
            mint=777,
            contract="0xbcFEbA7A9dA14f5C9453bDA72E2098537867B3c7",
            token_id="13530112",
            evidence_url="https://collectscan.com/token/0xbcFEbA7A9dA14f5C9453bDA72E2098537867B3c7/instance/13530112",
            mapping_method="manual-exact",
            expected_name="Spider-Man",
        )
        result = resolve_mapping(mapping)
        self.assertTrue(result.verified)
        self.assertEqual(result.owner, "0x1111111111111111111111111111111111111111")
        self.assertEqual(len(result.transfers), 1)

    @patch("grail.ownership._get_json")
    def test_metadata_mismatch_fails_closed(self, get_json):
        get_json.return_value = {
            "metadata": {"name": "Completely Different Collectible"},
            "owner": {"hash": "0x1111111111111111111111111111111111111111"},
        }
        mapping = TokenMapping(
            source_url="https://example/c/spider-man",
            mint=777,
            contract="0xbcFEbA7A9dA14f5C9453bDA72E2098537867B3c7",
            token_id="13530112",
            evidence_url="https://collectscan.com/token/0xbcFEbA7A9dA14f5C9453bDA72E2098537867B3c7/instance/13530112",
            mapping_method="manual-exact",
            expected_name="Spider-Man",
        )
        result = resolve_mapping(mapping)
        self.assertFalse(result.verified)
        self.assertIsNone(result.owner)


if __name__ == "__main__":
    unittest.main()
